from uuid import uuid4

from fastapi import APIRouter, Depends, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.errors import AppError
from app.models import EventLog, User
from app.schemas.auth import CreateManagedUserRequest, UserActiveRequest
from app.schemas.serializers import serialize_user
from app.security.dependencies import require_roles
from app.security.passwords import hash_password

router = APIRouter(prefix="/api", tags=["users"])
admin_user = require_roles("admin")


@router.get("/users")
def list_users(
    _admin: User = Depends(admin_user), db: Session = Depends(get_db)
) -> dict[str, list[dict]]:
    users = db.scalars(select(User).order_by(User.created_at.desc(), User.name, User.id)).all()
    return {"items": [serialize_user(user) for user in users]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_managed_user(
    payload: CreateManagedUserRequest,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> dict:
    email = str(payload.email).strip().lower()
    username = payload.username.strip().lower()
    duplicate = db.scalar(
        select(User.id).where(or_(func.lower(User.email) == email, func.lower(User.username) == username))
    )
    if duplicate:
        raise AppError(409, "user_conflict", "That email or username is already in use")

    user = User(
        id=f"USER-{uuid4().hex}",
        name=payload.name,
        email=email,
        username=username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        approval_status="approved",
        city=payload.city,
        worker_id=f"WKR-{uuid4().hex[:12].upper()}" if payload.role == "worker" else None,
        is_active=True,
        source="admin_created",
    )
    db.add(user)
    db.add(EventLog(
        actor_user_id=admin.id,
        action="account_created_by_admin",
        object_type="user",
        object_id=user.id,
        summary=f"Created {payload.role} account {email}",
        details={"role": payload.role, "approval_status": "approved"},
        source="auth",
    ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "user_conflict", "That email or username is already in use") from exc
    db.refresh(user)
    return serialize_user(user)


@router.patch("/users/{user_id}/status")
def set_user_status(
    user_id: str,
    payload: UserActiveRequest,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "User was not found")
    if user.id == admin.id and not payload.is_active:
        raise AppError(409, "self_deactivation", "You cannot deactivate your own account")
    if user.role == "admin" and user.is_active and not payload.is_active:
        active_admins = db.scalar(
            select(func.count()).select_from(User).where(
                User.role == "admin", User.approval_status == "approved", User.is_active.is_(True)
            )
        )
        if active_admins <= 1:
            raise AppError(409, "last_admin", "The last active administrator cannot be deactivated")

    user.is_active = payload.is_active
    db.add(EventLog(
        actor_user_id=admin.id,
        action="account_activated" if payload.is_active else "account_deactivated",
        object_type="user",
        object_id=user.id,
        summary=f"{'Activated' if payload.is_active else 'Deactivated'} account {user.email}",
        details={"is_active": payload.is_active},
        source="auth",
    ))
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.get("/users/pending")
def list_pending_users(
    _admin: User = Depends(admin_user), db: Session = Depends(get_db)
) -> dict[str, list[dict]]:
    users = db.scalars(
        select(User).where(User.approval_status == "pending").order_by(User.created_at, User.id)
    ).all()
    return {"items": [serialize_user(user) for user in users]}


@router.post("/users/{user_id}/approve")
def approve_user(
    user_id: str,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "User was not found")
    if user.approval_status != "pending":
        raise AppError(409, "approval_conflict", "Only pending accounts can be approved")

    user.role = "worker"  # Publicly registered accounts can never become administrators.
    user.approval_status = "approved"
    user.is_active = True
    user.worker_id = user.worker_id or f"WKR-{uuid4().hex[:12].upper()}"
    db.add(EventLog(
        actor_user_id=admin.id,
        action="account_approved",
        object_type="user",
        object_id=user.id,
        summary=f"Approved worker account {user.email}",
        details={"approval_status": "approved", "role": "worker", "worker_id": user.worker_id},
        source="auth",
    ))
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(409, "approval_conflict", "The account could not be approved") from exc
    db.refresh(user)
    return serialize_user(user)


@router.post("/users/{user_id}/reject")
def reject_user(
    user_id: str,
    admin: User = Depends(admin_user),
    db: Session = Depends(get_db),
) -> dict:
    user = db.get(User, user_id)
    if user is None:
        raise AppError(404, "user_not_found", "User was not found")
    if user.approval_status != "pending":
        raise AppError(409, "approval_conflict", "Only pending accounts can be rejected")

    user.approval_status = "rejected"
    user.is_active = False
    db.add(EventLog(
        actor_user_id=admin.id,
        action="account_rejected",
        object_type="user",
        object_id=user.id,
        summary=f"Rejected access request {user.email}",
        details={"approval_status": "rejected"},
        source="auth",
    ))
    db.commit()
    db.refresh(user)
    return serialize_user(user)


@router.get("/workers")
def list_workers(
    _admin: User = Depends(admin_user), db: Session = Depends(get_db)
) -> dict[str, list[dict]]:
    workers = db.scalars(
        select(User)
        .where(User.role == "worker", User.approval_status == "approved", User.is_active.is_(True))
        .order_by(User.name, User.id)
    ).all()
    return {
        "items": [
            {
                "id": user.id,
                "worker_id": user.worker_id,
                "name": user.name,
                "email": user.email,
                "city": user.city,
                "status": "ACTIVE",
            }
            for user in workers
        ]
    }
