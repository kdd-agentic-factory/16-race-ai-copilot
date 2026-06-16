from __future__ import annotations

from typing import Any

from ..clients.rag_cag_client import RAGCAGClient
from ..contracts import KnowledgeCitation, KnowledgeRetrievalResult, RequestContext


class KnowledgeRetrievalService:
    """Retrieve grounded citations with a safe fallback when RAG is unavailable."""

    def __init__(self, rag_cag_client: RAGCAGClient | None = None):
        self.rag_cag_client = rag_cag_client or RAGCAGClient()

    async def retrieve(
        self,
        query: str,
        context: RequestContext | None = None,
        limit: int = 5,
    ) -> KnowledgeRetrievalResult:
        context = context or RequestContext.from_values(tenant_id="tenant-default")

        try:
            rag_results = await self.rag_cag_client.search_context(query=query, top_k=limit)
            citations = self._build_citations(rag_results, context)
            if citations:
                return KnowledgeRetrievalResult(
                    query=query,
                    citations=citations,
                    fallback_used=False,
                    audit=self._build_audit(context, fallback_used=False),
                )
        except Exception:
            pass

        return KnowledgeRetrievalResult(
            query=query,
            citations=[self._fallback_citation(query, context)],
            fallback_used=True,
            audit=self._build_audit(context, fallback_used=True),
        )

    def _build_citations(
        self, rag_results: dict[str, Any] | None, context: RequestContext
    ) -> list[KnowledgeCitation]:
        if not rag_results:
            return []

        sources = rag_results.get("sources") or rag_results.get("results") or []
        citations: list[KnowledgeCitation] = []
        for source in sources:
            if not isinstance(source, dict):
                continue
            source_tenant = source.get("tenant_id")
            if source_tenant not in (None, context.tenant_id):
                continue
            citations.append(
                KnowledgeCitation(
                    source_id=source.get("id", source.get("source_id", "rag-cag:unknown")),
                    title=source.get("title", source.get("name", "RAG/CAG Source")),
                    snippet=source.get("snippet", source.get("text", source.get("content", ""))),
                    url_or_path=source.get("url", source.get("path")),
                    confidence=float(source.get("confidence", source.get("score", 0.0)) or 0.0),
                    tenant_id=context.tenant_id,
                    request_id=context.request_id,
                    session_id=context.session_id,
                    correlation_id=context.correlation_id,
                    fallback_used=False,
                )
            )
        return citations

    def _fallback_citation(self, query: str, context: RequestContext) -> KnowledgeCitation:
        return KnowledgeCitation(
            source_id="rag-cag:fallback",
            title="Grounding fallback",
            snippet=(
                "Fallback: RAG/CAG returned no citations, so the copilot can only "
                f"provide a recommendation to investigate: {query}."
            ),
            confidence=0.0,
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            session_id=context.session_id,
            correlation_id=context.correlation_id,
            fallback_used=True,
        )

    def _build_audit(self, context: RequestContext, fallback_used: bool) -> dict[str, Any]:
        return {
            "tenant_id": context.tenant_id,
            "user_role": context.user_role,
            "request_scope": context.approval_scope.value,
            "request_id": context.request_id,
            "session_id": context.session_id,
            "correlation_id": context.correlation_id,
            "fallback_used": fallback_used,
        }
