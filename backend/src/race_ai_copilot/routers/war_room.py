"""SLA War Room integration router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from ..auth_deps import get_request_context
from ..contracts import RequestContext, WarRoomRequestEnvelope, WarRoomResponseEnvelope
from ..services.sla_war_room_service import SlaWarRoomService

router = APIRouter(tags=["war-room"])

_DEFAULT_WAR_ROOM_SERVICE = SlaWarRoomService()


async def get_war_room_service() -> SlaWarRoomService:
    return _DEFAULT_WAR_ROOM_SERVICE


@router.post("/war-room", response_model=WarRoomResponseEnvelope)
@router.post("/sla-war-room", response_model=WarRoomResponseEnvelope)
async def sla_war_room(
    request: WarRoomRequestEnvelope,
    service: Annotated[SlaWarRoomService, Depends(get_war_room_service)],
    request_context: Annotated[RequestContext, Depends(get_request_context)],
) -> WarRoomResponseEnvelope:
    if request.context.request_id is None:
        request = request.model_copy(update={"context": request_context})
    return service.route(request)
