from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Account, AuthSession
from app.schemas.auth import AccountListItem, AccountListResponse, AuthResponse, AuthUserResponse, RegisterRequest


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


class AuthService:
    session_days = 30

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def register(self, db: Session, payload: RegisterRequest) -> AuthResponse:
        self._validate_invite_code(payload)
        existing = db.scalar(select(Account).where(Account.username == payload.username))
        if existing is not None:
            raise ValueError("用户名已注册")
        account = Account(
            username=payload.username,
            display_name=payload.display_name,
            role=payload.role,
            password_hash=self._hash_password(payload.password),
        )
        db.add(account)
        db.flush()
        response = self._create_session(db, account)
        db.commit()
        return response

    def _validate_invite_code(self, payload: RegisterRequest) -> None:
        allowed_codes = (
            self.settings.counselor_invite_codes
            if payload.role == "counselor"
            else self.settings.visitor_invite_codes
        )
        if not allowed_codes:
            raise ValueError("当前未开放注册，请联系管理员配置邀请码")
        if not any(hmac.compare_digest(payload.invite_code, code) for code in allowed_codes):
            raise ValueError("邀请码无效")

    def login(self, db: Session, username: str, password: str) -> AuthResponse:
        account = db.scalar(select(Account).where(Account.username == username.strip()))
        if account is None or not self._verify_password(password, account.password_hash):
            raise ValueError("用户名或密码错误")
        response = self._create_session(db, account)
        db.commit()
        return response

    def list_accounts(self, db: Session) -> AccountListResponse:
        accounts = list(db.scalars(select(Account).order_by(Account.role, Account.created_at.desc(), Account.id.desc())).all())
        active_ids = set(self.settings.active_counselor_ids)
        items = [
            AccountListItem(
                id=account.id,
                username=account.username,
                display_name=account.display_name,
                role=account.role,
                active_for_human_letters=account.role == "counselor" and account.username in active_ids,
                created_at=_serialize_datetime(account.created_at),
            )
            for account in accounts
        ]
        return AccountListResponse(
            items=items,
            total=len(items),
            visitor_count=sum(1 for account in accounts if account.role == "visitor"),
            counselor_count=sum(1 for account in accounts if account.role == "counselor"),
            active_counselor_count=sum(
                1 for account in accounts if account.role == "counselor" and account.username in active_ids
            ),
        )

    def authenticate(self, db: Session, token: str) -> Account | None:
        token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
        session = db.scalar(
            select(AuthSession).where(
                AuthSession.token_hash == token_hash,
                AuthSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if session is None:
            return None
        return db.get(Account, session.account_id)

    def _create_session(self, db: Session, account: Account) -> AuthResponse:
        token = secrets.token_urlsafe(32)
        db.add(
            AuthSession(
                account_id=account.id,
                token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
                expires_at=datetime.now(timezone.utc) + timedelta(days=self.session_days),
            )
        )
        return AuthResponse(token=token, user=self._to_user(account))

    def _hash_password(self, password: str) -> str:
        salt = secrets.token_bytes(16)
        derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
        return f"pbkdf2_sha256${salt.hex()}${derived.hex()}"

    def _verify_password(self, password: str, encoded: str) -> bool:
        try:
            algorithm, salt_hex, expected_hex = encoded.split("$", 2)
            if algorithm != "pbkdf2_sha256":
                return False
            derived = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                bytes.fromhex(salt_hex),
                310_000,
            )
            return hmac.compare_digest(derived.hex(), expected_hex)
        except ValueError:
            return False

    def _to_user(self, account: Account) -> AuthUserResponse:
        return AuthUserResponse(
            id=account.id,
            username=account.username,
            display_name=account.display_name,
            role=account.role,
        )
