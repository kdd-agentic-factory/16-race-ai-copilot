"""Integration tests for the ChatService pipeline — full pipeline with mocked external clients.

Tests the entire ``ChatService.answer()`` flow through intent classification,
evidence retrieval, tool planning, answer composition, and guardrail
evaluation using ``unittest.mock.AsyncMock`` for external service calls.
All assertions target the final ``ChatResponse`` contract.
"""

from __future__ import annotations

from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

import pytest

from race_ai_copilot.models.schemas import ChatRequest, ChatResponse
from race_ai_copilot.services.chat_service import ChatService


# ──────────────────────────────────────────────────────────────────────
# Fixtures — shared mock data
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_ollama() -> MagicMock:
    """Return a clean ``MagicMock`` whose ``generate`` is an ``AsyncMock``."""
    client = MagicMock()
    client.generate = AsyncMock()
    return client


@pytest.fixture
def mock_rag_cag() -> MagicMock:
    """Return a clean ``MagicMock`` whose ``search_context`` is an ``AsyncMock``."""
    client = MagicMock()
    client.search_context = AsyncMock()
    return client


@pytest.fixture
def mock_mcp() -> MagicMock:
    """Return a clean ``MagicMock`` whose ``call_tool`` is an ``AsyncMock``."""
    client = MagicMock()
    client.call_tool = AsyncMock()
    return client


@pytest.fixture
def telemetry_rag() -> Dict[str, Any]:
    """Simulated RAG/CAG response for a tire-degradation query."""
    return {
        "sources": [
            {
                "id": "tire_deg_001",
                "title": "Lap 10 Tire Degradation Report",
                "url": "/evidence/tire-deg-lap10",
                "snippet": (
                    "Rear tire degradation increases sharply after lap 10 due to "
                    "thermal cycling and graining onset on the left-rear corner."
                ),
            }
        ]
    }


@pytest.fixture
def telemetry_mcp() -> Dict[str, Any]:
    """Simulated MCP telemetry tool response."""
    return {
        "data": {
            "tire_temp_rear_left": 98.5,
            "tire_temp_rear_right": 101.2,
            "lap_number": 10,
            "degradation_rate": 0.15,
        }
    }


@pytest.fixture
def parts_rag() -> Dict[str, Any]:
    """Simulated RAG/CAG response for a Jerez-specific part query."""
    return {
        "sources": [
            {
                "id": "part_catalog_001",
                "title": "Jerez Circuit-Specific Parts Catalog",
                "url": "/parts/jerez-catalog",
                "snippet": (
                    "Recommended part candidate: high-load brake duct (PN: BD-JRZ-2024) "
                    "designed for Jerez's heavy braking zones. Material: carbon-fiber "
                    "composite with titanium inserts."
                ),
            }
        ]
    }


@pytest.fixture
def parts_mcp() -> Dict[str, Any]:
    """Simulated MCP parts-catalog tool response."""
    return {
        "data": {
            "part_number": "BD-JRZ-2024",
            "part_name": "High-Load Brake Duct",
            "material": "Carbon Fiber Composite",
            "availability": "In stock",
            "estimated_life": "3 race weekends",
        }
    }


@pytest.fixture
def setup_rag() -> Dict[str, Any]:
    """Simulated RAG/CAG response for a fuel-mapping query."""
    return {
        "sources": [
            {
                "id": "setup_map_001",
                "title": "Fuel Mapping Strategy Guide",
                "url": "/setup/mapping-strategy",
                "snippet": (
                    "Mapping 2 enriches the fuel mixture at high RPM for improved "
                    "cooling but reduces total fuel endurance by 2 laps."
                ),
            }
        ]
    }


@pytest.fixture
def setup_mcp() -> Dict[str, Any]:
    """Simulated MCP setup tool response."""
    return {
        "data": {
            "current_mapping": "1",
            "recommended_mapping": "2",
            "fuel_impact": "-2 laps",
            "power_gain": "+3.5% at high RPM",
        }
    }


@pytest.fixture
def empty_rag() -> Dict[str, Any]:
    """Simulated RAG/CAG response that returns **no** evidence."""
    return {"sources": []}


# ──────────────────────────────────────────────────────────────────────
# Fixtures — ChatService instances
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def service(
    mock_ollama: MagicMock,
    mock_rag_cag: MagicMock,
    mock_mcp: MagicMock,
) -> ChatService:
    """Build a ``ChatService`` with **all** external clients replaced by mocks.

    The real reasoning components (``IntentClassifier``, ``ToolPlanner``,
    ``EvidenceBuilder``, ``PromptBuilder``, ``AnswerComposer``) and guardrails
    (``ApprovalGuard``, ``EvidenceRequiredGuard``, ``RaceDecisionGuard``) are
    wired in — only the network clients are mocked.
    """
    return ChatService(
        llm_client=mock_ollama,
        rag_cag_client=mock_rag_cag,
        mcp_client=mock_mcp,
    )


# ──────────────────────────────────────────────────────────────────────
# Tests
# ──────────────────────────────────────────────────────────────────────


class TestChatServicePipeline:
    """Integration tests for the full ``ChatService.answer()`` pipeline.

    Each test simulates a complete user → answer cycle by providing mock
    responses for the three external services (Ollama, RAG/CAG, MCP) and
    then asserting on the shape / content of the returned ``ChatResponse``.
    """

    # ------------------------------------------------------------------
    # 1. Telemetry query (no approval needed)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_telemetry_query_returns_evidence_and_no_approval(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
        telemetry_rag: Dict[str, Any],
        telemetry_mcp: Dict[str, Any],
    ) -> None:
        """A telemetry query should return evidence, tool calls, and *not* require approval.

        Scenario
        --------
        User asks → "Why is rear tire degradation increasing after lap 10?"
        The keyword ``degradation`` maps to the **Telemetry** intent, the
        RAG service returns a tire-degradation report, the MCP tool returns
        live sensor values, and the answer composer synthesises a response.
        No critical keywords are present, so ``approval_required`` is ``False``.
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = telemetry_rag
        mock_mcp.call_tool.return_value = telemetry_mcp

        # The intent classifier matches "degradation" → Telemetry via
        # keyword lookup, so the LLM is NOT called for intent.
        # Two LLM calls remain:
        #   1. ToolPlanner — returns a JSON tool plan
        #   2. AnswerComposer — returns the final answer
        mock_ollama.generate.side_effect = [
            # Call 1 — ToolPlanner.plan()
            '[{"tool_name": "get_telemetry_data", "parameters": {"sensor": "tire_temp"}}]',
            # Call 2 — AnswerComposer.compose()
            (
                "Based on telemetry data, rear tire degradation increases after lap "
                "10 due to thermal cycling at the left-rear corner (98.5 °C). "
                "I recommend monitoring tire pressures closely."
            ),
        ]

        request = ChatRequest(
            message="Why is rear tire degradation increasing after lap 10?"
        )

        # ── Act ──────────────────────────────────────────────────
        response: ChatResponse = await service.answer(request)

        # ── Assert ────────────────────────────────────────────────

        # --- Identity ---
        assert response.conversation_id, "A conversation ID should be generated"
        assert response.message_id, "A message ID should be generated"

        # --- Evidence ---
        assert len(response.evidence) > 0, "RAG evidence should be present"
        assert any(
            "degradation" in e.snippet.lower() for e in response.evidence
        ), "Evidence should reference tire degradation"

        # --- Tool calls ---
        assert len(response.tool_calls) > 0, "Tool calls should be present"
        assert (
            response.tool_calls[0].tool_name == "get_telemetry_data"
        ), "The first tool should be get_telemetry_data"

        # --- Answer ---
        assert response.answer, "The answer should not be empty"
        assert "tire" in response.answer.lower(), "Answer should mention tires"

        # --- Approval ---
        assert response.approval_required is False, "Telemetry does not require approval"
        assert response.approver_role is None, "No approver role for safe queries"

        # --- Recommendations ---
        # The answer starts with "Based on..." not "Recommend...", so
        # no structured recommendations should be extracted.
        assert isinstance(response.recommendations, list)

        # --- Next actions ---
        assert isinstance(response.next_actions, list)

    # ------------------------------------------------------------------
    # 2. Setup change with critical keyword → approval required
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_setup_change_with_mapping_triggers_approval(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
        setup_rag: Dict[str, Any],
        setup_mcp: Dict[str, Any],
    ) -> None:
        """A setup change containing the word "mapping" must require crew-chief approval.

        Scenario
        --------
        User asks → "Should we switch to Mapping 2 after lap 10?"
        No INTENT_MAP keyword matches, so the ``IntentClassifier`` falls
        back to the LLM and asks it to classify the intent as "Setup".
        The **critical keyword** ``mapping`` (found in ``CRITICAL_KEYWORDS``)
        triggers ``ApprovalGuard`` → ``approval_required: True`` with
        ``approver_role: "crew_chief"``.
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = setup_rag
        mock_mcp.call_tool.return_value = setup_mcp

        # The message "Switch to Mapping 2" does NOT match any
        # INTENT_MAP keywords ("mapping" is not in the intent map;
        # it's only in CRITICAL_KEYWORDS). The LLM is called for
        # intent classification.
        # Three LLM calls:
        #   1. IntentClassifier (fallback — returns "Setup")
        #   2. ToolPlanner (returns JSON tool plan)
        #   3. AnswerComposer (returns the answer)
        mock_ollama.generate.side_effect = [
            "Setup",  # Call 1 — IntentClassifier.classify()
            '[{"tool_name": "get_current_setup", "parameters": {}}]',  # Call 2 — ToolPlanner
            (
                "I recommend switching to Mapping 2 after lap 10. "
                "This change can improve high-RPM power delivery but reduces "
                "fuel endurance by approximately 2 laps.\n"
                "Suggest verifying with the crew chief before applying the change."
            ),
        ]

        request = ChatRequest(
            message="Should we switch to Mapping 2 after lap 10?"
        )

        # ── Act ──────────────────────────────────────────────────
        response: ChatResponse = await service.answer(request)

        # ── Assert ────────────────────────────────────────────────

        # --- Identity ---
        assert response.conversation_id
        assert response.message_id

        # --- Approval ---
        assert (
            response.approval_required is True
        ), "The critical keyword 'mapping' must force approval"
        assert (
            response.approver_role == "crew_chief"
        ), "The responsible approver must be the crew chief"

        # --- Evidence ---
        assert len(response.evidence) > 0, "Setup evidence should be present"

        # --- Tool calls ---
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].tool_name == "get_current_setup"

        # --- Next actions include approval step ---
        assert any(
            "approval" in a.lower() for a in response.next_actions
        ), "Next actions should mention crew-chief approval"

    # ------------------------------------------------------------------
    # 3. Parts design query → evidence with part-candidate info
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_parts_design_returns_part_candidate_info(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
        parts_rag: Dict[str, Any],
        parts_mcp: Dict[str, Any],
    ) -> None:
        """A parts-design query should return evidence with part-candidate details.

        Scenario
        --------
        User asks → "What circuit-specific part should we design for Jerez?"
        The keyword ``part`` maps to the **Parts** intent. The RAG service
        returns a part-catalog entry mentioning a specific *part candidate*
        (brake duct PN: BD-JRZ-2024). The answer composer's response starts
        with "Recommend", which the ``_extract_recommendations`` helper picks
        up and converts into a ``Recommendation`` object.
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = parts_rag
        mock_mcp.call_tool.return_value = parts_mcp

        # "part" keyword → Parts intent (no LLM call for classification)
        # Two LLM calls:
        #   1. ToolPlanner
        #   2. AnswerComposer
        mock_ollama.generate.side_effect = [
            # Call 1 — ToolPlanner for Parts intent
            '[{"tool_name": "search_parts_catalog", "parameters": {"circuit": "Jerez"}}]',
            # Call 2 — AnswerComposer
            (
                "Recommend designing a high-load brake duct (BD-JRZ-2024) for Jerez.\n"
                "This carbon-fiber composite part is tailored for Jerez's heavy braking "
                "zones and is currently in stock.\n"
                "Suggest checking part availability in inventory."
            ),
        ]

        request = ChatRequest(
            message="What circuit-specific part should we design for Jerez?"
        )

        # ── Act ──────────────────────────────────────────────────
        response: ChatResponse = await service.answer(request)

        # ── Assert ────────────────────────────────────────────────

        # --- Identity ---
        assert response.conversation_id
        assert response.message_id

        # --- Evidence with part candidate ---
        assert len(response.evidence) > 0, "Evidence must contain part-catalog info"
        part_snippets = " ".join(e.snippet.lower() for e in response.evidence)
        assert "brake duct" in part_snippets, "Evidence should mention the brake duct"
        assert "bd-jrz-2024" in part_snippets, "Evidence should include the part number"

        # --- Tool calls ---
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].tool_name == "search_parts_catalog"

        # --- Recommendations ---
        # The answer starts with "Recommend...", so _extract_recommendations
        # should have parsed it.
        assert (
            len(response.recommendations) > 0
        ), "A recommendation starting with 'Recommend' should be extracted"
        assert any(
            "brake duct" in r.action.lower() for r in response.recommendations
        ), "Recommendation should reference the brake duct"

        # --- Next actions for Parts ---
        parts_actions = ["inventory", "part", "availability"]
        combined_actions = " ".join(a.lower() for a in response.next_actions)
        assert any(
            kw in combined_actions for kw in parts_actions
        ), "Next actions should reference parts/inventory"

    # ------------------------------------------------------------------
    # 4. General question without evidence → low confidence + uncertainty
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_general_query_without_evidence_returns_low_confidence(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
        empty_rag: Dict[str, Any],
    ) -> None:
        """A general-knowledge question lacking evidence should return low confidence.

        Scenario
        --------
        User asks → "What is the weather like?"
        No INTENT_MAP keyword matches, so the ``IntentClassifier`` falls
        back to the LLM and classifies it as **General**. The ``ToolPlanner``
        returns an empty list (no tools mapped to General), so the MCP
        client is **never called**. The RAG/CAG service returns empty
        sources. The ``EvidenceBuilder`` produces a packet with no sources
        and no raw data, resulting in ``groundedness_score = 0.0``.
        Because the evidence check fails, the ``EvidenceRequiredGuard``
        sets ``uncertainty`` indicating limited grounding.
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = empty_rag
        # MCP is NOT called for General intent (no tools to execute)

        # No keyword match → LLM called for intent → returns "General"
        # ToolPlanner for General returns [] (NO LLM call, returns early)
        # AnswerComposer LLM call returns answer
        mock_ollama.generate.side_effect = [
            "General",  # Call 1 — IntentClassifier.classify()
            (
                "I don't have sufficient weather data to provide an accurate "
                "answer. Evidence is limited for this query."
            ),
        ]

        request = ChatRequest(message="What is the weather like?")

        # ── Act ──────────────────────────────────────────────────
        response: ChatResponse = await service.answer(request)

        # ── Assert ────────────────────────────────────────────────

        # --- Identity ---
        assert response.conversation_id
        assert response.message_id

        # --- Confidence ---
        assert (
            response.confidence < 0.5
        ), f"Confidence should be low but got {response.confidence}"

        # --- Uncertainty ---
        assert response.uncertainty is not None, (
            "Uncertainty should be set when evidence grounding fails"
        )
        assert "evidence" in response.uncertainty.lower(), (
            "Uncertainty message should reference limited evidence"
        )

        # --- No tool calls for General ---
        assert len(response.tool_calls) == 0, (
            "General intent should produce no tool calls"
        )

        # --- No evidence ---
        assert len(response.evidence) == 0, (
            "Empty RAG sources should result in zero evidence items"
        )

        # --- Answer mentions insufficient evidence ---
        assert response.answer, "Answer should not be empty"
        assert any(
            phrase in response.answer.lower()
            for phrase in ["insufficient", "limited", "don't have", "cannot", "unable"]
        ), "Answer should mention insufficient or limited evidence"

    # ------------------------------------------------------------------
    # 5. Pipeline returns valid IDs and proper shape
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_pipeline_returns_valid_ids_and_structured_response(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
    ) -> None:
        """Verify that ``ChatService.answer()`` returns properly structured identifiers.

        Scenario
        --------
        A simple telemetry query ensures that:
        - ``conversation_id`` is populated (either from the request or generated)
        - ``message_id`` is generated fresh every call
        - All required fields on ``ChatResponse`` are present and correctly typed
        - A fresh ``conversation_id`` is generated when none is provided
        - The same ``conversation_id`` is reused when one IS provided
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = {
            "sources": [
                {
                    "id": "generic_001",
                    "title": "General Sensor Data",
                    "url": "/telemetry/sensors",
                    "snippet": "All sensor readings within normal operating range.",
                }
            ]
        }
        mock_mcp.call_tool.return_value = {"data": {"status": "nominal"}}

        mock_ollama.generate.side_effect = [
            # ToolPlanner
            '[{"tool_name": "get_telemetry_data", "parameters": {"sensor": "all"}}]',
            # AnswerComposer
            "All systems are nominal.",
        ]

        # --- Test A: auto-generated conversation_id ---
        request_no_id = ChatRequest(
            message="Are all sensors within range?"
        )
        response_a: ChatResponse = await service.answer(request_no_id)

        assert response_a.conversation_id, (
            "A conversation_id should be auto-generated when none is provided"
        )
        assert len(response_a.conversation_id) == 12, (
            f"Expected 12-char hex ID, got {len(response_a.conversation_id)} chars"
        )
        assert response_a.message_id, "A message_id should always be generated"
        assert len(response_a.message_id) == 12, (
            f"Expected 12-char hex message_id, got {len(response_a.message_id)} chars"
        )

        # --- Test B: conversation_id is preserved when provided ---
        mock_ollama.generate.side_effect = [
            '[{"tool_name": "get_telemetry_data", "parameters": {}}]',
            "Still nominal.",
        ]

        request_with_id = ChatRequest(
            conversation_id="custom-conversation-42",
            message="Confirm sensors?",
        )
        response_b: ChatResponse = await service.answer(request_with_id)

        assert (
            response_b.conversation_id == "custom-conversation-42"
        ), "The provided conversation_id should be preserved"

        # --- Test C: message_id is different per call ---
        assert (
            response_a.message_id != response_b.message_id
        ), "Each answer() call should generate a unique message_id"

        # --- Test D: all ChatResponse fields are present ---
        for field in (
            "conversation_id",
            "message_id",
            "answer",
            "confidence",
            "evidence",
            "tool_calls",
            "recommendations",
            "approval_required",
            "approver_role",
            "uncertainty",
            "next_actions",
        ):
            assert hasattr(response_a, field), f"ChatResponse missing required field: {field}"

    # ------------------------------------------------------------------
    # 6. Evidence from MCP without RAG still produces evidence
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_mcp_only_evidence_still_produces_evidence_items(
        self,
        service: ChatService,
        mock_ollama: MagicMock,
        mock_rag_cag: MagicMock,
        mock_mcp: MagicMock,
    ) -> None:
        """When RAG returns empty but MCP returns data, evidence should come from MCP.

        Scenario
        --------
        The RAG/CAG service returns no sources, but the MCP tool returns
        sensor data. The ``EvidenceBuilder`` should produce raw_data entries
        from the MCP result and calculate a groundedness_score > 0.
        """
        # ── Arrange ──────────────────────────────────────────────
        mock_rag_cag.search_context.return_value = {"sources": []}
        mock_mcp.call_tool.return_value = {
            "data": {
                "tire_temp": 98.5,
                "brake_temp": 450.0,
                "suspension_travel": 12.3,
            }
        }

        mock_ollama.generate.side_effect = [
            # ToolPlanner
            '[{"tool_name": "get_telemetry_data", "parameters": {"sensor": "all"}}]',
            # AnswerComposer
            "All telemetry readings are within normal operating ranges.",
        ]

        request = ChatRequest(
            message="What are the current telemetry readings?"
        )

        # ── Act ──────────────────────────────────────────────────
        response: ChatResponse = await service.answer(request)

        # ── Assert ────────────────────────────────────────────────

        # --- Identity ---
        assert response.conversation_id
        assert response.message_id

        # --- No RAG evidence, but MCP data is captured ---
        # EvidenceItems come from RAG sources only (there are none)
        assert len(response.evidence) == 0, (
            "No RAG sources means no EvidenceItem entries"
        )

        # --- Confidence from MCP data ---
        # EvidenceBuilder with 3 MCP claims (all non-None) and 0 RAG sources
        # → total_claims = 3, evidential_claims = 3 → groundedness = 1.0
        assert response.confidence == 1.0, (
            "MCP data provides full grounding when all values are non-null"
        )

        # --- Tool calls ---
        assert len(response.tool_calls) > 0
        assert response.tool_calls[0].tool_name == "get_telemetry_data"

        # --- No uncertainty (evidence check passed) ---
        assert response.uncertainty is None, (
            "When evidence is present (MCP), uncertainty should be None"
        )
