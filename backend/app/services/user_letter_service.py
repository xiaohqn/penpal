import random

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.models import Account, UserLetter
from app.schemas.user_letter import UserLetterCreateRequest, UserLetterListResponse, UserLetterResponse


class UserLetterService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_letter(
        self,
        db: Session,
        user_id: str,
        payload: UserLetterCreateRequest,
    ) -> UserLetterResponse:
        assigned_counselor_id = None
        if payload.reply_source == "human":
            if not self.settings.counselor_features_enabled:
                raise ValueError("当前暂未开放咨询师人工回复")
            counselor_usernames = list(
                db.scalars(select(Account.username).where(Account.role == "counselor")).all()
            )
            if not counselor_usernames:
                raise ValueError("目前没有已注册的咨询师可以接收人工来信")
            assigned_counselor_id = random.choice(counselor_usernames)
        letter = UserLetter(
            user_id=user_id,
            signature=payload.signature or "匿名",
            letter_text=payload.letter_text,
            reply_text=payload.reply_text,
            reply_source=payload.reply_source or "ai",
            status=payload.status or "replied",
            response_preference=payload.response_preference,
            assigned_counselor_id=assigned_counselor_id,
        )
        db.add(letter)
        db.commit()
        db.refresh(letter)
        return UserLetterResponse.model_validate(letter)

    def list_letters(self, db: Session, user_id: str) -> UserLetterListResponse:
        total = db.scalar(
            select(func.count()).select_from(UserLetter).where(UserLetter.user_id == user_id)
        ) or 0
        letters = db.scalars(
            select(UserLetter).where(UserLetter.user_id == user_id).order_by(desc(UserLetter.created_at))
        ).all()
        return UserLetterListResponse(
            items=[UserLetterResponse.model_validate(letter) for letter in letters],
            total=total,
        )

    def list_assigned_letters(self, db: Session, counselor_id: str) -> UserLetterListResponse:
        total = db.scalar(
            select(func.count())
            .select_from(UserLetter)
            .where(UserLetter.assigned_counselor_id == counselor_id)
        ) or 0
        letters = db.scalars(
            select(UserLetter)
            .where(UserLetter.assigned_counselor_id == counselor_id)
            .order_by(desc(UserLetter.created_at))
        ).all()
        return UserLetterListResponse(
            items=[UserLetterResponse.model_validate(letter) for letter in letters],
            total=total,
        )

    def get_letter(self, db: Session, user_id: str, letter_id: int) -> UserLetterResponse | None:
        letter = db.scalar(
            select(UserLetter).where(UserLetter.id == letter_id, UserLetter.user_id == user_id)
        )
        if letter is None:
            return None
        return UserLetterResponse.model_validate(letter)

    def update_status(
        self,
        db: Session,
        user_id: str,
        letter_id: int,
        status: str,
    ) -> UserLetterResponse | None:
        letter = db.scalar(
            select(UserLetter).where(UserLetter.id == letter_id, UserLetter.user_id == user_id)
        )
        if letter is None:
            return None
        letter.status = status
        db.commit()
        db.refresh(letter)
        return UserLetterResponse.model_validate(letter)

    def submit_counselor_reply(
        self,
        db: Session,
        counselor_id: str,
        letter_id: int,
        reply_text: str,
    ) -> UserLetterResponse | None:
        letter = db.scalar(
            select(UserLetter).where(
                UserLetter.id == letter_id,
                UserLetter.assigned_counselor_id == counselor_id,
            )
        )
        if letter is None:
            return None
        letter.reply_text = reply_text
        letter.reply_source = "human"
        letter.status = "replied"
        db.commit()
        db.refresh(letter)
        return UserLetterResponse.model_validate(letter)
