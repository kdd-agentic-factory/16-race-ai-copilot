#!/usr/bin/env python3
"""Main evaluation runner for the 16-race-ai-copilot.

Loads a dataset from ``evals/datasets/``, runs each prompt through the
copilot's ``ChatService`` pipeline (with mocked external clients), and
evaluates every response against a battery of quality metrics.

Usage:
    python evals/run_eval.py --dataset copilot-prompts-v1
    python evals/run_eval.py --dataset copilot-prompts-v1 --verbose
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# ──────────────────────────────────────────────────────────────────────
# Path setup
# ──────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent  # project root
_BACKEND_SRC = _PROJECT_ROOT / "backend" / "src"

for _p in str(_BACKEND_SRC), str(_PROJECT_ROOT):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# TODO(sdk): If tests need copilot-api components too, add:
# sys.path.insert(0, str(_PROJECT_ROOT / "services" / "copilot-api"))

from race_ai_copilot.models.schemas import (
    ChatRequest,
    ChatResponse,
    EvidencePacket,
    ToolCallRecord,
)
from race_ai_copilot.reasoning.evidence_planner import EvidenceBuilder
from race_ai_copilot.services.chat_service import ChatService

from evals.metrics.approval_compliance import ApprovalComplianceMetric
from evals.metrics.evidence_coverage import EvidenceCoverageMetric
from evals.metrics.groundedness import GroundednessMetric
from evals.metrics.hallucination_risk import HallucinationRiskMetric
from evals.metrics.tool_precision import ToolPrecisionMetric


# ══════════════════════════════════════════════════════════════════════
# Mock components
# ══════════════════════════════════════════════════════════════════════


class MockOllamaClient:
    """Mock LLM client — returns pre-configured responses."""

    def __init__(self, default_response: str = "General"):
        self.default_response = default_response

    async def generate(
        self, prompt: str, options: Optional[Dict[str, Any]] = None
    ) -> str:
        return self.default_response

    async def chat(
        self,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        return self.default_response


class MockRAGCAGClient:
    """Mock RAG/CAG client — returns pre-configured evidence sources."""

    def __init__(self, evidence_sources: List[Dict[str, str]]):
        self.evidence_sources = evidence_sources

    async def search_context(
        self, query: str, top_k: int = 5
    ) -> Dict[str, Any]:
        return {
            "sources": [
                {
                    "id": src.get("id", f"src-{i}"),
                    "title": src.get("title", ""),
                    "url": src.get("url", ""),
                    "snippet": src.get("snippet", ""),
                    "text": src.get("text", src.get("snippet", "")),
                }
                for i, src in enumerate(self.evidence_sources)
            ]
        }


class MockMCPClient:
    """Mock MCP client — returns a generic success payload."""

    async def call_tool(
        self, tool_name: str, payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "data": {"tool": tool_name, "result": f"Mock result for {tool_name}"},
        }


class MockIntentClassifier:
    """Mock intent classifier — returns the pre-configured intent."""

    def __init__(self, intent: str):
        self._intent = intent

    async def classify(self, text: str) -> str:
        return self._intent


class MockToolPlanner:
    """Mock tool planner — returns the pre-configured tool calls."""

    def __init__(self, tool_names: List[str]):
        self._tool_names = tool_names

    async def plan(
        self, intent: str, query: str
    ) -> List[ToolCallRecord]:
        return [
            ToolCallRecord(tool_name=name, parameters={})
            for name in self._tool_names
        ]


class MockPromptBuilder:
    """Mock prompt builder — returns a simple grounded prompt."""

    def build_grounded_prompt(
        self,
        query: str,
        history: List[Dict[str, str]],
        evidence: Optional[EvidencePacket] = None,
        tool_trace: Optional[List[ToolCallRecord]] = None,
    ) -> str:
        return (
            f"System: You are the Race AI Copilot.\n"
            f"Evidence: {evidence.sources if evidence else 'none'}\n"
            f"Query: {query}"
        )


class MockAnswerComposer:
    """Mock answer composer — returns the pre-configured answer."""

    def __init__(self, answer: str):
        self._answer = answer

    async def compose(self, prompt: str, stream: bool = False) -> str:
        return self._answer


# ══════════════════════════════════════════════════════════════════════
# Dataset handling
# ══════════════════════════════════════════════════════════════════════


def load_dataset(
    name: str, datasets_dir: str = "evals/datasets"
) -> List[Dict[str, Any]]:
    """Load the named dataset from the datasets directory.

    Args:
        name: Dataset name (without ``.jsonl`` extension).
        datasets_dir: Path to the datasets directory.

    Returns:
        A list of parsed JSON entries.
    """
    path = Path(datasets_dir) / f"{name}.jsonl"
    if not path.exists():
        print(f"ERROR: Dataset not found at {path.resolve()}")
        sys.exit(1)

    entries: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                entries.append(json.loads(stripped))

    print(f"Loaded {len(entries)} prompts from {name}")
    return entries


# ══════════════════════════════════════════════════════════════════════
# Per-prompt evaluation
# ══════════════════════════════════════════════════════════════════════


async def evaluate_prompt(
    entry: Dict[str, Any],
) -> Dict[str, Any]:
    """Run a single prompt through the mocked pipeline and evaluate.

    Args:
        entry: A single dataset entry with ``prompt``, ``intent``,
            ``expected_tools``, ``requires_approval``,
            ``requires_evidence``, ``expected_answer``, and
            ``evidence_sources``.

    Returns:
        A dict with the response, called tools, approval status, and
        metric scores.
    """
    # ---- Build mock components from the entry data ----
    mock_llm = MockOllamaClient()
    mock_rag = MockRAGCAGClient(entry.get("evidence_sources", []))
    mock_mcp = MockMCPClient()
    mock_intent = MockIntentClassifier(entry.get("intent", "General"))
    mock_tools = MockToolPlanner(entry.get("expected_tools", []))
    mock_prompt = MockPromptBuilder()
    mock_composer = MockAnswerComposer(
        entry.get("expected_answer", "")
    )

    # Use the real EvidenceBuilder — it's stateless and will correctly
    # parse the mock RAG/MCP outputs into an EvidencePacket.
    real_evidence_builder = EvidenceBuilder()

    # ---- Build the ChatService with real guardrails ----
    service = ChatService(
        llm_client=mock_llm,
        rag_cag_client=mock_rag,
        mcp_client=mock_mcp,
        intent_classifier=mock_intent,
        tool_planner=mock_tools,
        evidence_builder=real_evidence_builder,
        prompt_builder=mock_prompt,
        answer_composer=mock_composer,
    )

    # ---- Create the request ----
    request = ChatRequest(
        message=entry["prompt"],
        require_evidence=entry.get("requires_evidence", True),
        context={},
    )

    # ---- Run the pipeline ----
    response: ChatResponse = await service.answer(request)

    # ---- Extract data for metrics ----
    called_tools: List[str] = [tc.tool_name for tc in response.tool_calls]
    evidence_packet_for_metrics = EvidencePacket(
        sources=response.evidence,
        raw_data=[],
        groundedness_score=response.confidence,
    )

    # ---- Compute metrics ----
    groundedness = GroundednessMetric()
    groundedness_score = groundedness.evaluate(
        response.answer, evidence_packet_for_metrics
    )

    evidence_coverage = EvidenceCoverageMetric()
    expected_snippets: List[str] = [
        s.get("snippet", s.get("text", ""))
        for s in entry.get("evidence_sources", [])
    ]
    evidence_coverage_score = evidence_coverage.evaluate(
        response, expected_snippets
    )

    tool_precision = ToolPrecisionMetric()
    expected_tools: List[str] = entry.get("expected_tools", [])
    tool_f1 = tool_precision.evaluate(called_tools, expected_tools)
    tool_prec = tool_precision.precision(called_tools, expected_tools)
    tool_rec = tool_precision.recall(called_tools, expected_tools)

    approval = ApprovalComplianceMetric()
    approval_compliance = approval.evaluate(
        response, entry.get("requires_approval", False)
    )

    hallucination = HallucinationRiskMetric()
    hallucination_risk = hallucination.evaluate(
        response.answer, evidence_packet_for_metrics
    )

    return {
        "prompt": entry["prompt"],
        "intent": entry.get("intent", "?"),
        "expected_tools": expected_tools,
        "called_tools": called_tools,
        "expected_approval": entry.get("requires_approval", False),
        "approval_required": response.approval_required,
        "answer": response.answer,
        "confidence": response.confidence,
        "metrics": {
            "groundedness": groundedness_score,
            "evidence_coverage": evidence_coverage_score,
            "tool_precision": tool_prec,
            "tool_recall": tool_rec,
            "tool_f1": tool_f1,
            "approval_compliance": approval_compliance,
            "hallucination_risk": hallucination_risk,
        },
    }


async def run_all(
    entries: List[Dict[str, Any]],
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Evaluate all prompts sequentially.

    Args:
        entries: The dataset entries.
        verbose: If ``True``, print per-prompt details.

    Returns:
        A list of result dicts, one per prompt.
    """
    results: List[Dict[str, Any]] = []
    n = len(entries)

    for i, entry in enumerate(entries):
        if verbose:
            print(f"\n[{i + 1}/{n}] Evaluating: {entry['prompt'][:70]}...")

        result = await evaluate_prompt(entry)
        results.append(result)

        if verbose:
            _print_per_prompt(result)

    return results


# ══════════════════════════════════════════════════════════════════════
# Reporting
# ══════════════════════════════════════════════════════════════════════


def _print_per_prompt(result: Dict[str, Any]) -> None:
    """Print detailed results for a single prompt."""
    m = result["metrics"]
    print(f"  Intent        : {result['intent']}")
    print(f"  Groundedness  : {m['groundedness']:.3f}")
    print(f"  Evidence Cov. : {m['evidence_coverage']:.3f}")
    print(f"  Tool F1       : {m['tool_f1']:.3f}")
    print(f"  Approval Comp.: {m['approval_compliance']}")
    print(f"  Halluc. Risk  : {m['hallucination_risk']:.3f}")
    print(f"  Called tools  : {result['called_tools']}")
    print(f"  Expected tools: {result['expected_tools']}")
    print(f"  Approval req. : {result['approval_required']} (expected: {result['expected_approval']})")


def print_summary(results: List[Dict[str, Any]]) -> None:
    """Print the aggregated summary table."""
    n = len(results)
    if n == 0:
        print("No results to report.")
        return

    # Aggregate
    avg_groundedness = sum(r["metrics"]["groundedness"] for r in results) / n
    avg_evidence_cov = sum(r["metrics"]["evidence_coverage"] for r in results) / n
    avg_tool_prec = sum(r["metrics"]["tool_precision"] for r in results) / n
    avg_tool_rec = sum(r["metrics"]["tool_recall"] for r in results) / n
    avg_tool_f1 = sum(r["metrics"]["tool_f1"] for r in results) / n
    approval_rate = sum(
        1 for r in results if r["metrics"]["approval_compliance"]
    ) / n
    avg_hallucination = sum(
        r["metrics"]["hallucination_risk"] for r in results
    ) / n

    # Output
    print()
    print("=" * 72)
    print("  RACE AI COPILOT — EVALUATION SUMMARY")
    print("=" * 72)
    print(f"  Dataset                : {n} prompts")
    print()

    header = f"  {'Metric':<30} {'Avg Score':<10}"
    sep = f"  {'-'*30} {'-'*10}"
    print(header)
    print(sep)
    print(f"  {'Groundedness':<30} {avg_groundedness:<10.3f}")
    print(f"  {'Evidence Coverage':<30} {avg_evidence_cov:<10.3f}")
    print(f"  {'Tool Precision':<30} {avg_tool_prec:<10.3f}")
    print(f"  {'Tool Recall':<30} {avg_tool_rec:<10.3f}")
    print(f"  {'Tool F1':<30} {avg_tool_f1:<10.3f}")
    print(f"  {'Approval Compliance Rate':<30} {approval_rate:<10.3f}")
    print(f"  {'Hallucination Risk':<30} {avg_hallucination:<10.3f}")
    print()

    # Warnings
    warnings: List[str] = []
    if avg_hallucination > 0.3:
        warnings.append(
            "! Hallucination risk ({:.2f}) exceeds 0.3 -- "
            "investigate flagged prompts.".format(avg_hallucination)
        )
    if avg_groundedness < 0.7:
        warnings.append(
            "! Groundedness ({:.2f}) is below 0.7 -- "
            "evidence pipeline may need attention.".format(avg_groundedness)
        )
    if approval_rate < 0.9:
        warnings.append(
            "! Approval compliance ({:.2%}) is below 90% -- "
            "approval guard may need tuning.".format(approval_rate)
        )
    if avg_groundedness < 0.7:
        warnings.append(
            f"!  Groundedness ({avg_groundedness:.2f}) is below 0.7 — "
            "evidence pipeline may need attention."
        )
    if approval_rate < 0.9:
        warnings.append(
            f"!  Approval compliance ({approval_rate:.2%}) is below 90% — "
            "approval guard may need tuning."
        )
    if avg_groundedness < 0.7:
        warnings.append(
            f"⚠  Groundedness ({avg_groundedness:.2f}) is below 0.7 — "
            "evidence pipeline may need attention."
        )
    if approval_rate < 0.9:
        warnings.append(
            f"⚠  Approval compliance ({approval_rate:.2%}) is below 90% — "
            "approval guard may need tuning."
        )

    if warnings:
        print("  Warnings:")
        for w in warnings:
            print(f"  {w}")
        print()

    # Per-prompt breakdown (compact)
    print("  Per-prompt breakdown:")
    print(
        f"  {'#':<3} {'Tool F1':<9} {'Grounded':<10} {'Hluc. Risk':<12} "
        f"{'Approval':<9} {'Intent':<20}"
    )
    print(f"  {'-'*3} {'-'*9} {'-'*10} {'-'*12} {'-'*9} {'-'*20}")
    for i, r in enumerate(results):
        m = r["metrics"]
        ok = "PASS" if m["approval_compliance"] else "FAIL"
        print(
            f"  {i + 1:<3} {m['tool_f1']:<9.3f} {m['groundedness']:<10.3f} "
            f"{m['hallucination_risk']:<12.3f} {ok:<9} {r['intent']:<20}"
        )
    print()


# ══════════════════════════════════════════════════════════════════════
# CLI entry point
# ══════════════════════════════════════════════════════════════════════


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate the Race AI Copilot against a prompt dataset."
    )
    parser.add_argument(
        "--dataset",
        default="copilot-prompts-v1",
        help="Dataset name (without .jsonl). Default: copilot-prompts-v1",
    )
    parser.add_argument(
        "--datasets-dir",
        default="evals/datasets",
        help="Path to the datasets directory. Default: evals/datasets",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print per-prompt metric breakdown.",
    )
    return parser.parse_args()


def main() -> None:
    """Load dataset, run evaluation, print summary."""
    args = parse_args()

    print(f"Race AI Copilot — Evaluation Runner")
    print(f"{'=' * 72}")

    entries = load_dataset(args.dataset, args.datasets_dir)
    results = asyncio.run(run_all(entries, verbose=args.verbose))
    print_summary(results)


if __name__ == "__main__":
    main()
