from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_counselor_id
from app.api.deps import get_auth_service, get_db_session
from app.schemas.auth import AccountListResponse, AuthResponse, LoginRequest, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        return auth_service.register(db=db, payload=payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=AuthResponse)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> AuthResponse:
    try:
        return auth_service.login(db=db, username=payload.username, password=payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    _: str = Depends(get_counselor_id),
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> AccountListResponse:
    return auth_service.list_accounts(db=db)
