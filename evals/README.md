# Evaluation Framework — 16-race-ai-copilot

## Purpose

The evaluation framework measures the quality, safety, and reliability of
the Race AI Copilot's responses. It provides a systematic way to:

- **Validate grounding** — ensure answers are supported by retrieved evidence.
- **Detect hallucinations** — flag claims that reference data not present
  in the evidence packet.
- **Check tool accuracy** — verify the right tools were called for the
  user's intent.
- **Enforce approval compliance** — confirm critical actions are flagged
  for crew-chief approval.
- **Track regressions** — compare metric scores across different model
  versions or prompt changes.

## How to run

```bash
# From the project root
python evals/run_eval.py --dataset copilot-prompts-v1
```

The script automatically adds `backend/src` to `sys.path` so it can import
the copilot's `ChatService`, schemas, and reasoning components.

### Options

| Flag            | Default               | Description                              |
|-----------------|-----------------------|------------------------------------------|
| `--dataset`     | `copilot-prompts-v1`  | Name of the dataset (without `.jsonl`)   |
| `--datasets-dir`| `evals/datasets`      | Path to the datasets directory           |
| `--verbose`     | `False`               | Print per-prompt metric breakdown        |

## Available datasets

| Dataset               | Prompts | Coverage                                                   |
|-----------------------|---------|------------------------------------------------------------|
| `copilot-prompts-v1`  | 10      | Telemetry, Setup, Parts, Simulation, Reports, General      |

Each dataset is a JSONL file where every line contains:

```json
{
  "prompt": "User's question to the copilot",
  "intent": "Expected intent classification",
  "requires_evidence": true,
  "requires_approval": false,
  "expected_tools": ["tool1", "tool2"],
  "expected_answer": "Canned ideal answer for metric comparison",
  "evidence_sources": [
    {"id": "src1", "title": "...", "snippet": "..."}
  ]
}
```

## Metrics measured

| Metric                  | Range    | What it measures                                    |
|-------------------------|----------|-----------------------------------------------------|
| Groundedness            | 0.0–1.0  | Fraction of claims in the answer supported by evidence |
| Evidence Coverage       | 0.0–1.0  | How much of the expected evidence was actually presented |
| Tool Precision          | 0.0–1.0  | Precision of tool calls against expected tools      |
| Tool Recall             | 0.0–1.0  | Recall of tool calls against expected tools         |
| Approval Compliance     | 0 or 1   | Whether approval requirements were correctly flagged |
| Hallucination Risk      | 0.0–1.0  | Higher values = more unsupported claims detected    |

### Interpreting results

- **Groundedness ≥ 0.8**: The answer is well-supported by evidence.
- **Hallucination Risk ≤ 0.2**: Low risk of fabricated data.
- **Approval Compliance = 1.0**: Critical actions are correctly gated.
- **Tool Precision ≥ 0.8**: The pipeline is selecting appropriate tools.
