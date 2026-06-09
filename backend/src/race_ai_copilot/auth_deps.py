"""Authentication dependencies for the Race AI Copilot.

Provides ``get_current_principal`` — a FastAPI dependency that returns the
authenticated principal from one of three sources (in order of precedence):

1. JWT claims set by ``InsForgeAuthMiddleware`` (``request.state.insforge_claims``)
2. ``X-Principal-ID`` / ``X-Principal-Role`` trusted headers (internal proxies)
3. A local-dev fallback principal (when neither JWT nor trusted headers are present)

Usage::

    @router.post("/chat")
    async def chat(
        request: ChatRequest,
        principal: Principal = Depends(get_current_principal),
    ):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from fastapi import Depends, HTTPException, Request, status


@dataclass(frozen=True)
class Principal:
    """Authenticated caller identity."""

    user_id: str
    role: str = "viewer"
    name: str = ""
    claims: dict = field(default_factory=dict)

    @property
    def is_crew_chief(self) -> bool:
        """Return True when the principal holds a crew-chief-equivalent role."""
        return self.role in ("crew_chief", "admin", "race_engineer", "team_principal")

    @property
    def is_system(self) -> bool:
        """Return True when the principal is the local-dev / system fallback."""
        return self.user_id.startswith("system-")


def _resolve_principal_from_claims(request: Request) -> Optional[Principal]:
    """Try to build a Principal from JWT claims set by InsForgeAuthMiddleware."""
    claims: Optional[dict] = getattr(request.state, "insforge_claims", None)
    if not claims:
        return None
    return Principal(
        user_id=claims.get("sub", claims.get("user_id", "unknown")),
        role=claims.get("role", claims.get("app_metadata", {}).get("role", "viewer")),
        name=claims.get("name", claims.get("preferred_username", "")),
        claims=claims,
    )


def _resolve_principal_from_headers(request: Request) -> Optional[Principal]:
    """Try to build a Principal from trusted proxy headers."""
    principal_id = request.headers.get("X-Principal-ID")
    if not principal_id:
        return None
    return Principal(
        user_id=principal_id,
        role=request.headers.get("X-Principal-Role", "viewer"),
        name=request.headers.get("X-Principal-Name", principal_id),
    )


def _local_dev_principal() -> Principal:
    """Return a system principal for local development."""
    return Principal(
        user_id="system-local-dev",
        role="admin",
        name="Local Developer",
    )


async def get_current_principal(request: Request) -> Principal:
    """Dependency: resolve the authenticated principal.

    Resolution order:
      1. JWT claims from ``InsForgeAuthMiddleware``
      2. Trusted proxy headers (``X-Principal-ID`` + ``X-Principal-Role``)
      3. Local-dev fallback (system principal)

    In production with ``INSFORGE_AUTH_ENABLED=true``, the JWT path will
    always resolve — if the JWT is missing or invalid the middleware already
    returns a 401 before reaching this dependency.
    """
    principal = (
        _resolve_principal_from_claims(request)
        or _resolve_principal_from_headers(request)
        or _local_dev_principal()
    )
    return principal


def require_role(*roles: str):
    """Dependency factory: require the caller to hold one of the given roles.

    Usage::

        @router.post("/admin")
        async def admin_only(
            principal: Principal = Depends(require_role("admin", "team_principal")),
        ):
            ...
    """

    async def _role_checker(request: Request, principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{principal.role}' is not authorized for this action. "
                f"Required one of: {', '.join(roles)}.",
            )
        return principal

    return _role_checker
