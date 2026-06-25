"""Query routes: submit natural language query, fetch result."""

from uuid import UUID

from fastapi import APIRouter, Query

from app.api.auth_deps import CurrentUser, DbSession
from app.schemas.query import (
    InvestigationResponse,
    QueryListResponse,
    QueryRequest,
    QueryResponse,
)
from app.services import query_service

router = APIRouter(prefix="/query", tags=["query"])


@router.post("", response_model=QueryResponse, status_code=201)
async def submit_query(
    input: QueryRequest, user: CurrentUser, session: DbSession
) -> QueryResponse:
    if user.org_id is None:
        from app.core.exceptions import PermissionDenied

        raise PermissionDenied("user has no organization")
    return await query_service.submit_query(
        input, user_id=user.id, org_id=user.org_id, session=session
    )


@router.get("/queries", response_model=QueryListResponse)
async def list_queries(
    user: CurrentUser,
    session: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
) -> QueryListResponse:
    from base64 import b64decode, b64encode
    from datetime import datetime
    from sqlalchemy import select
    from app.models import Query as QueryModel

    if user.org_id is None:
        from app.core.exceptions import PermissionDenied

        raise PermissionDenied("user has no organization")

    query = (
        select(QueryModel)
        .where(QueryModel.org_id == user.org_id)
        .order_by(QueryModel.created_at.desc(), QueryModel.id.desc())
        .limit(limit + 1)
    )
    if cursor:
        try:
            decoded = b64decode(cursor).decode()
            created_str, last_id = decoded.split("|", 1)
            last_created = datetime.fromisoformat(created_str)
            query = query.where(
                (QueryModel.created_at < last_created)
                | (
                    (QueryModel.created_at == last_created)
                    & (QueryModel.id < UUID(last_id))
                )
            )
        except Exception:
            pass

    result = await session.scalars(query)
    queries = list(result)
    has_more = len(queries) > limit
    if has_more:
        queries = queries[:limit]

    items = [QueryResponse.model_validate(q) for q in queries]
    next_cursor = None
    if has_more and queries:
        last = queries[-1]
        next_cursor = b64encode(
            f"{last.created_at.isoformat()}|{last.id}".encode()
        ).decode()

    return QueryListResponse(items=items, next_cursor=next_cursor, has_more=has_more)


@router.get("/queries/{query_id}", response_model=QueryResponse)
async def get_query(
    query_id: UUID, user: CurrentUser, session: DbSession
) -> QueryResponse:
    if user.org_id is None:
        from app.core.exceptions import PermissionDenied

        raise PermissionDenied("user has no organization")
    return await query_service.get_query(query_id, user.org_id, session)


@router.get("/investigations/{investigation_id}", response_model=InvestigationResponse)
async def get_investigation(
    investigation_id: UUID, user: CurrentUser, session: DbSession
) -> InvestigationResponse:
    if user.org_id is None:
        from app.core.exceptions import PermissionDenied

        raise PermissionDenied("user has no organization")
    return await query_service.get_investigation(investigation_id, user.org_id, session)
