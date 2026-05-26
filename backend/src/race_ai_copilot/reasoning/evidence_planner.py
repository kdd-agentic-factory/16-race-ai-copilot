from typing import Dict, Any, Optional

from ..models.schemas import EvidencePacket, EvidenceItem


class EvidenceBuilder:
    """Constructs an EvidencePacket from RAG/CAG and MCP results.

    The builder takes raw search and tool results, extracts structured
    sources and raw data, and calculates a ``groundedness_score`` based
    on the ratio of evidential claims to total claims.
    """

    def build(
        self,
        rag_results: Optional[Dict[str, Any]] = None,
        mcp_results: Optional[Dict[str, Any]] = None,
    ) -> EvidencePacket:
        """Build an EvidencePacket from the provided results.

        Args:
            rag_results: Response from the RAG/CAG ``search_context`` call.
            mcp_results: Response from an MCP ``call_tool`` execution.

        Returns:
            An ``EvidencePacket`` containing extracted sources, raw data,
            and a calculated groundedness score.
        """
        sources: list[EvidenceItem] = []
        raw_data: list[str] = []
        total_claims = 0
        evidential_claims = 0

        # ---- Process RAG / CAG results ----
        if rag_results:
            rag_sources = rag_results.get("sources", rag_results.get("results", []))
            for src in rag_sources:
                if isinstance(src, dict):
                    sources.append(
                        EvidenceItem(
                            id=src.get("id", src.get("source_id", "rag:unknown")),
                            title=src.get("title", src.get("name", "RAG Source")),
                            url_or_path=src.get(
                                "url", src.get("path", "")
                            ),
                            snippet=src.get(
                                "snippet",
                                src.get("text", src.get("content", "")),
                            ),
                        )
                    )
                    evidential_claims += 1
                    total_claims += 1
                else:
                    raw_data.append(str(src))
                    total_claims += 1

        # ---- Process MCP results ----
        # mcp_results is either a flat {"data": {...}} result or an accumulated
        # {"tool_name": {"data": {...}}, ...} dict produced by ChatService.
        if mcp_results:
            # Detect accumulated format: all values are dicts with a "data" key
            is_accumulated = all(
                isinstance(v, dict) and ("data" in v or "result" in v)
                for v in mcp_results.values()
            ) if mcp_results else False

            if is_accumulated:
                all_data: Dict[str, Any] = {}
                for tool_result in mcp_results.values():
                    payload = tool_result.get("data", tool_result.get("result", {}))
                    if isinstance(payload, dict):
                        all_data.update(payload)
            else:
                all_data = mcp_results.get("data", mcp_results.get("result", {}))

            data_items = (
                all_data.items()
                if isinstance(all_data, dict)
                else (
                    [(str(i), item) for i, item in enumerate(all_data)]
                    if isinstance(all_data, list)
                    else [("result", all_data)]
                )
            )
            for key, value in data_items:
                raw_data.append(f"{key}: {value}")
                total_claims += 1
                if value is not None:
                    evidential_claims += 1

        groundedness_score = (
            evidential_claims / total_claims if total_claims > 0 else 0.0
        )

        return EvidencePacket(
            sources=sources,
            raw_data=raw_data,
            groundedness_score=groundedness_score,
        )
