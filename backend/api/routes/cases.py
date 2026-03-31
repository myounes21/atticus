"""Case management API routes (Admin only).

CRUD for cases: create, list, get, update, delete.
Uses in-memory storage for development.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from backend.api.middleware.rbac_middleware import admin_only, any_authenticated
from backend.core.dependencies import CurrentUser, get_current_user
from backend.db.postgres import (
    execute,
    execute_returning_one,
    fetch_all,
    fetch_optional,
)
from backend.schemas.case import (
    CaseCreate,
    CaseListResponse,
    LawyerListResponse,
    LawyerOption,
    CaseResponse,
    CaseUpdate,
)
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/cases", tags=["cases"])


def _resolve_assigned_lawyers(
    requested_lawyers: list[uuid.UUID],
) -> list[uuid.UUID]:
    if not requested_lawyers:
        lawyer_rows = fetch_all("SELECT user_id FROM users WHERE role = 'lawyer'")
        return [row["user_id"] for row in lawyer_rows]

    deduped = list(dict.fromkeys(requested_lawyers))
    found_rows = fetch_all(
        "SELECT user_id, role FROM users WHERE user_id = ANY(%s::uuid[])",
        (deduped,),
    )
    found_by_id = {row["user_id"]: row["role"] for row in found_rows}

    invalid_ids = [
        str(user_id) for user_id in deduped if found_by_id.get(user_id) != "lawyer"
    ]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "assigned_lawyers must contain valid lawyer user IDs only. "
                f"Invalid: {', '.join(invalid_ids)}"
            ),
        )
    return deduped


@router.post(
    "/demo/reset",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_only)],
)
def reset_demo_case_data() -> None:
    """Reset and reseed deterministic demo content (admin only)."""
    if settings.app_env.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo reset is disabled in production",
        )
    from backend.scripts.reset_and_seed_demo_data import (
        main as reset_and_seed_demo_data,
    )

    reset_and_seed_demo_data()


@router.post(
    "",
    response_model=CaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(admin_only)],
)
def create_case(
    payload: CaseCreate,
    user: CurrentUser = Depends(get_current_user),
) -> CaseResponse:
    """Create a new case."""
    if len(payload.name) > settings.max_case_name_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Case name exceeds {settings.max_case_name_chars} characters",
        )
    if (
        payload.client_name
        and len(payload.client_name) > settings.max_client_name_chars
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Client name exceeds {settings.max_client_name_chars} characters",
        )

    assigned_lawyers = _resolve_assigned_lawyers(list(payload.assigned_lawyers))

    case_id = uuid.uuid4()
    row = execute_returning_one(
        """
        INSERT INTO cases (case_id, name, client_name, status, closed_at, created_by, assigned_lawyers)
        VALUES (%s, %s, %s, 'active', NULL, %s, %s::uuid[])
        RETURNING *
        """,
        (
            case_id,
            payload.name,
            payload.client_name,
            user.user_id,
            assigned_lawyers,
        ),
    )
    logger.info("Created case '%s' (%s)", payload.name, case_id)
    return CaseResponse(**row)


@router.get("", response_model=CaseListResponse)
def list_cases(
    user: CurrentUser = Depends(get_current_user),
) -> CaseListResponse:
    """List cases visible to the current user."""
    if user.role == "admin":
        visible = fetch_all("SELECT * FROM cases ORDER BY created_at DESC")
    else:
        visible = fetch_all(
            "SELECT * FROM cases WHERE %s = ANY(assigned_lawyers) ORDER BY created_at DESC",
            (user.user_id,),
        )

    cases = [CaseResponse(**c) for c in visible]
    return CaseListResponse(cases=cases, total=len(cases))


@router.get(
    "/lawyers", response_model=LawyerListResponse, dependencies=[Depends(admin_only)]
)
def list_lawyers_for_assignment() -> LawyerListResponse:
    rows = fetch_all(
        """
        SELECT user_id, email, full_name
          FROM users
         WHERE role = 'lawyer'
         ORDER BY COALESCE(NULLIF(BTRIM(full_name), ''), email)
        """
    )
    lawyers = [
        LawyerOption(
            user_id=row["user_id"],
            email=row["email"],
            full_name=(row.get("full_name") or row["email"].split("@", maxsplit=1)[0]),
        )
        for row in rows
    ]
    return LawyerListResponse(lawyers=lawyers, total=len(lawyers))


@router.get("/{case_id}", response_model=CaseResponse)
def get_case(
    case_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
) -> CaseResponse:
    """Get a single case by ID."""
    case = fetch_optional("SELECT * FROM cases WHERE case_id = %s", (case_id,))
    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    if user.role != "admin" and user.user_id not in (case["assigned_lawyers"] or []):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not assigned to this case"
        )

    return CaseResponse(**case)


@router.patch(
    "/{case_id}",
    response_model=CaseResponse,
    dependencies=[Depends(admin_only)],
)
def update_case(case_id: uuid.UUID, payload: CaseUpdate) -> CaseResponse:
    """Update a case (admin only)."""
    if payload.name is not None and len(payload.name) > settings.max_case_name_chars:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Case name exceeds {settings.max_case_name_chars} characters",
        )
    if (
        payload.client_name is not None
        and len(payload.client_name) > settings.max_client_name_chars
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Client name exceeds {settings.max_client_name_chars} characters",
        )

    existing = fetch_optional(
        "SELECT case_id FROM cases WHERE case_id = %s", (case_id,)
    )
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    assigned_lawyers = (
        _resolve_assigned_lawyers(list(payload.assigned_lawyers))
        if payload.assigned_lawyers is not None
        else None
    )

    row = execute_returning_one(
        """
        UPDATE cases
           SET name = COALESCE(%s, name),
               client_name = COALESCE(%s, client_name),
               status = COALESCE(%s, status),
               closed_at = CASE
                   WHEN %s = 'closed' THEN NOW()
                   ELSE closed_at
               END,
               assigned_lawyers = COALESCE(%s::uuid[], assigned_lawyers)
         WHERE case_id = %s
     RETURNING *
        """,
        (
            payload.name,
            payload.client_name,
            payload.status,
            payload.status,
            assigned_lawyers,
            case_id,
        ),
    )
    return CaseResponse(**row)


@router.delete(
    "/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(admin_only)],
)
def delete_case(case_id: uuid.UUID) -> None:
    """Delete a case (admin only)."""
    existing = fetch_optional(
        "SELECT case_id FROM cases WHERE case_id = %s", (case_id,)
    )
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Case not found"
        )

    execute("DELETE FROM cases WHERE case_id = %s", (case_id,))
    logger.info("Deleted case %s", case_id)
