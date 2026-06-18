from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_auth_service, get_db_session
from app.db.models import Account
from app.services.auth_service import AuthService


def get_current_account(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db_session),
    auth_service: AuthService = Depends(get_auth_service),
) -> Account:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    account = auth_service.authenticate(db=db, token=authorization.removeprefix("Bearer ").strip())
    if account is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已失效，请重新登录")
    return account


def get_counselor_id(account: Account = Depends(get_current_account)) -> str:
    if account.role != "counselor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅咨询师可访问")
    return account.username


def get_user_id(account: Account = Depends(get_current_account)) -> str:
    return account.username
