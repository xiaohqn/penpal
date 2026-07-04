import random
from datetime import datetime, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings
from app.db.models import Account, ConsultationRecord, ConversationMemory, MailMessage, MailThread, RiskAssessment, UserLetter
from app.schemas.mail_thread import (
    CounselorThreadReplyRequest,
    MailThreadArchiveResponse,
    MailMessageCreateRequest,
    MailThreadCreateRequest,
    MailThreadListResponse,
    MailThreadResponse,
)
from app.schemas.record import ConsultationRecordSaveRequest
from app.services.orchestration_service import OrchestrationService
from app.services.record_service import RecordService
from app.services.safety_service import RISK_ORDER, SafetyAssessment, SafetyService, max_risk_level

AI_REPLY_SIGNATURE = "心灵笔友 AI 陪伴员"


def _datetime_sort_value(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class MailThreadService:
    def __init__(
        self,
        settings: Settings,
        safety_service: SafetyService | None = None,
        orchestration_service: OrchestrationService | None = None,
        record_service: RecordService | None = None,
    ) -> None:
        self.settings = settings
        self.safety_service = safety_service or SafetyService()
        self.orchestration_service = orchestration_service
        self.record_service = record_service

    async def create_thread(self, db: Session, user_id: str, payload: MailThreadCreateRequest) -> MailThreadResponse:
        user_assessment = self.safety_service.assess_user_letter(
            payload.content,
            previous_levels=self._previous_user_risk_levels(db, user_id),
        )
        forced_human = RISK_ORDER[user_assessment.risk_level] >= RISK_ORDER["HIGH"]
        crisis = user_assessment.risk_level == "CRISIS"
        if payload.reply_mode == "human" and not self.settings.counselor_features_enabled:
            raise ValueError("当前暂未开放咨询师人工回复")
        reply_mode = "human" if forced_human and self.settings.counselor_features_enabled else payload.reply_mode
        assigned_counselor_id = None
        if reply_mode == "human":
            assigned_counselor_id = self._pick_counselor_or_none(db) if forced_human else self._pick_counselor(db)

        should_generate_later = reply_mode == "ai" and not payload.ai_reply_text and not crisis
        thread = MailThread(
            user_id=user_id,
            signature=payload.signature or "匿名",
            title=self._build_title(payload.content),
            reply_mode=reply_mode,
            response_preference="理性分析",
            status="crisis" if crisis else ("waiting_counselor" if reply_mode == "human" else ("waiting_ai" if should_generate_later else "waiting_user")),
            assigned_counselor_id=assigned_counselor_id,
        )
        db.add(thread)
        db.flush()
        user_message = MailMessage(
            thread_id=thread.id,
            sender_type="user",
            sender_id=user_id,
            content=payload.content,
            status="sent",
        )
        db.add(user_message)
        db.flush()
        self._record_risk(db, user_id, thread.id, user_message.id, "user_letter", user_assessment)
        if crisis:
            crisis_text = self.safety_service.crisis_reply(
                counselor_available=self.settings.counselor_features_enabled
            )
            crisis_text = self._with_ai_signature(crisis_text)
            reply_assessment = self.safety_service.assess_reply(crisis_text)
            db.add(
                MailMessage(
                    thread_id=thread.id,
                    sender_type="ai",
                    sender_id="mindful-ai",
                    content=crisis_text,
                    status="sent",
                )
            )
            db.flush()
            ai_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
            self._record_risk(db, user_id, thread.id, ai_message.id if ai_message else None, "ai_reply", reply_assessment)
        elif forced_human and not self.settings.counselor_features_enabled:
            reply_text = self.safety_service.safe_fallback_reply(counselor_available=False)
            reply_text = self._with_ai_signature(reply_text)
            reply_assessment = self.safety_service.assess_reply(reply_text)
            thread.status = "waiting_user"
            db.add(
                MailMessage(
                    thread_id=thread.id,
                    sender_type="ai",
                    sender_id="mindful-ai",
                    content=reply_text,
                    status="sent",
                )
            )
            db.flush()
            ai_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
            self._record_risk(db, user_id, thread.id, ai_message.id if ai_message else None, "ai_reply", reply_assessment)
        elif reply_mode == "ai":
            if payload.ai_reply_text:
                self._append_ai_reply(db=db, thread=thread, reply_text=payload.ai_reply_text)
        db.commit()
        self.rebuild_memory(db, thread.id)
        db.expire_all()
        return self.get_thread(db, user_id, thread.id)  # type: ignore[return-value]

    def list_threads(self, db: Session, user_id: str) -> MailThreadListResponse:
        self._migrate_legacy_letters(db, user_id=user_id)
        total = db.scalar(select(func.count()).select_from(MailThread).where(MailThread.user_id == user_id)) or 0
        threads = db.scalars(
            select(MailThread)
            .where(MailThread.user_id == user_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
            .order_by(desc(MailThread.updated_at))
        ).all()
        return MailThreadListResponse(items=[MailThreadResponse.model_validate(thread) for thread in threads], total=total)

    def get_thread(self, db: Session, user_id: str, thread_id: int) -> MailThreadResponse | None:
        self._migrate_legacy_letters(db, user_id=user_id)
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id, MailThread.user_id == user_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
        )
        if thread is None:
            return None
        return MailThreadResponse.model_validate(thread)

    async def add_user_message(
        self,
        db: Session,
        user_id: str,
        thread_id: int,
        payload: MailMessageCreateRequest,
    ) -> MailThreadResponse | None:
        thread = db.scalar(select(MailThread).where(MailThread.id == thread_id, MailThread.user_id == user_id))
        if thread is None:
            return None
        user_assessment = self.safety_service.assess_user_letter(
            payload.content,
            previous_levels=self._previous_user_risk_levels(db, user_id),
        )
        db.add(
            MailMessage(
                thread_id=thread.id,
                sender_type="user",
                sender_id=user_id,
                content=payload.content,
                status="sent",
            )
        )
        db.flush()
        latest_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
        self._record_risk(db, user_id, thread.id, latest_message.id if latest_message else None, "user_letter", user_assessment)
        forced_human = RISK_ORDER[user_assessment.risk_level] >= RISK_ORDER["HIGH"]
        crisis = user_assessment.risk_level == "CRISIS"
        if forced_human and self.settings.counselor_features_enabled:
            thread.reply_mode = "human"
            thread.status = "crisis" if crisis else "waiting_counselor"
            if thread.assigned_counselor_id is None:
                thread.assigned_counselor_id = self._pick_counselor_or_none(db)
            if crisis:
                crisis_text = self.safety_service.crisis_reply(
                    counselor_available=self.settings.counselor_features_enabled
                )
                crisis_text = self._with_ai_signature(crisis_text)
                db.add(
                    MailMessage(
                        thread_id=thread.id,
                        sender_type="ai",
                        sender_id="mindful-ai",
                        content=crisis_text,
                        status="sent",
                    )
                )
                db.flush()
                ai_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
                self._record_risk(
                    db,
                    user_id,
                    thread.id,
                    ai_message.id if ai_message else None,
                    "ai_reply",
                    self.safety_service.assess_reply(crisis_text),
                )
        elif forced_human and not self.settings.counselor_features_enabled:
            reply_text = (
                self.safety_service.crisis_reply(counselor_available=False)
                if crisis
                else self.safety_service.safe_fallback_reply(counselor_available=False)
            )
            reply_text = self._with_ai_signature(reply_text)
            db.add(
                MailMessage(
                    thread_id=thread.id,
                    sender_type="ai",
                    sender_id="mindful-ai",
                    content=reply_text,
                    status="sent",
                )
            )
            db.flush()
            ai_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
            self._record_risk(
                db,
                user_id,
                thread.id,
                ai_message.id if ai_message else None,
                "ai_reply",
                self.safety_service.assess_reply(reply_text),
            )
            thread.status = "waiting_user"
        elif thread.reply_mode == "ai":
            if payload.ai_reply_text:
                self._append_ai_reply(db=db, thread=thread, reply_text=payload.ai_reply_text)
            else:
                thread.status = "waiting_ai"
        else:
            thread.status = "waiting_counselor" if self.settings.counselor_features_enabled else "waiting_user"
        db.commit()
        self.rebuild_memory(db, thread.id)
        db.expire_all()
        return self.get_thread(db, user_id, thread.id)

    def archive_ai_reply_to_records(self, db: Session, user_id: str, thread_id: int) -> MailThreadArchiveResponse | None:
        if self.record_service is None:
            raise ValueError("Record service is not configured")
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id, MailThread.user_id == user_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.risk_assessments))
        )
        if thread is None:
            return None
        messages = sorted(thread.messages, key=lambda message: (_datetime_sort_value(message.created_at), message.id))
        latest_ai = next((message for message in reversed(messages) if message.sender_type == "ai"), None)
        if latest_ai is None:
            raise ValueError("当前会话还没有可入库的 AI 回信")
        latest_user = next(
            (
                message
                for message in reversed(messages)
                if message.sender_type == "user" and _datetime_sort_value(message.created_at) <= _datetime_sort_value(latest_ai.created_at)
            ),
            None,
        )
        if latest_user is None:
            raise ValueError("当前会话缺少对应的用户来信")
        latest_risk = next(
            (assessment for assessment in reversed(thread.risk_assessments) if assessment.target_type == "user_letter"),
            None,
        )
        persona_name = self._persona_for_preference(thread.response_preference)
        planner_output = {
            "intention": "用户对 AI 回信满意后主动选择入库",
            "core_issue": self._compact(latest_user.content, 120),
            "risk_assessment": latest_risk.reasoning if latest_risk is not None else "",
            "generation_plan": "用户认可这封 AI 回信对其来信有帮助，作为后续 RAG 参考样本。",
            "style_summary": {"persona_name": persona_name},
        }
        existing_record = self._find_user_satisfied_record(
            db=db,
            user_id=user_id,
            thread_id=thread.id,
            ai_message_id=latest_ai.id,
        )
        if existing_record is not None:
            existing_record.rag_ready = "approved"
            db.commit()
            return MailThreadArchiveResponse(record_id=existing_record.id, rag_ready=existing_record.rag_ready)

        record = self.record_service.create_record(
            db=db,
            counselor_id=f"user:{user_id}",
            payload=ConsultationRecordSaveRequest(
                user_input=latest_user.content,
                selected_persona_name=persona_name,
                selected_style_config={"persona_name": persona_name, "source": "user_satisfied_ai_reply"},
                planner_output=planner_output,
                draft_candidates=[
                    {
                        "draft_id": f"mail-thread-{thread.id}-ai-{latest_ai.id}",
                        "persona_name": persona_name,
                        "source": "mail_thread_ai",
                        "source_label": "用户满意 AI 回信",
                        "planner_output": planner_output,
                        "response": latest_ai.content,
                        "raw_response": latest_ai.content,
                    }
                ],
                ai_selected_raw_response=latest_ai.content,
                expert_polished_response=latest_ai.content,
                expert_annotation="用户对 AI 回信满意并主动选择入库。",
                rag_ready="approved",
                sample_reason="user_satisfied_ai_reply",
                risk_assessment={
                    "risk_level": latest_risk.risk_level if latest_risk is not None else "NONE",
                    "signals": latest_risk.signals_json if latest_risk is not None else [],
                    "reasoning": latest_risk.reasoning if latest_risk is not None else "",
                },
                sample_snapshot={"mail_thread_id": thread.id, "ai_message_id": latest_ai.id},
            ),
        )
        return MailThreadArchiveResponse(record_id=record.id, rag_ready=record.rag_ready)

    def unarchive_ai_reply_from_records(self, db: Session, user_id: str, thread_id: int) -> MailThreadArchiveResponse | None:
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id, MailThread.user_id == user_id)
            .options(selectinload(MailThread.messages))
        )
        if thread is None:
            return None
        messages = sorted(thread.messages, key=lambda message: (_datetime_sort_value(message.created_at), message.id))
        latest_ai = next((message for message in reversed(messages) if message.sender_type == "ai"), None)
        if latest_ai is None:
            raise ValueError("当前会话还没有可取消入库的 AI 回信")
        record = self._find_user_satisfied_record(
            db=db,
            user_id=user_id,
            thread_id=thread.id,
            ai_message_id=latest_ai.id,
        )
        if record is None:
            raise ValueError("这封 AI 回信尚未加入样本库")
        record.rag_ready = "rejected"
        db.commit()
        return MailThreadArchiveResponse(record_id=record.id, rag_ready=record.rag_ready)

    def _find_user_satisfied_record(
        self,
        db: Session,
        user_id: str,
        thread_id: int,
        ai_message_id: int,
    ) -> ConsultationRecord | None:
        records = db.scalars(
            select(ConsultationRecord)
            .where(
                ConsultationRecord.counselor_id == f"user:{user_id}",
                ConsultationRecord.sample_reason == "user_satisfied_ai_reply",
            )
            .order_by(desc(ConsultationRecord.created_at))
            .limit(20)
        ).all()
        for record in records:
            snapshot = record.sample_snapshot_json or {}
            if snapshot.get("mail_thread_id") == thread_id and snapshot.get("ai_message_id") == ai_message_id:
                return record
        return None

    def complete_thread(self, db: Session, user_id: str, thread_id: int) -> MailThreadResponse | None:
        thread = db.scalar(select(MailThread).where(MailThread.id == thread_id, MailThread.user_id == user_id))
        if thread is None:
            return None
        thread.status = "completed"
        db.commit()
        self.rebuild_memory(db, thread.id)
        return self.get_thread(db, user_id, thread.id)

    def list_assigned_threads(self, db: Session, counselor_id: str) -> MailThreadListResponse:
        total = db.scalar(
            select(func.count()).select_from(MailThread).where(MailThread.assigned_counselor_id == counselor_id)
        ) or 0
        threads = db.scalars(
            select(MailThread)
            .where(MailThread.assigned_counselor_id == counselor_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
            .order_by(desc(MailThread.updated_at))
        ).all()
        return MailThreadListResponse(items=[MailThreadResponse.model_validate(thread) for thread in threads], total=total)

    def get_assigned_thread(self, db: Session, counselor_id: str, thread_id: int) -> MailThreadResponse | None:
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id, MailThread.assigned_counselor_id == counselor_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
        )
        return MailThreadResponse.model_validate(thread) if thread is not None else None

    def build_workspace_input(self, thread: MailThreadResponse) -> str:
        latest_user_message = next(
            (message for message in reversed(thread.messages) if message.sender_type == "user"),
            None,
        )
        return latest_user_message.content if latest_user_message is not None else thread.title

    def build_workspace_context(self, thread: MailThreadResponse) -> dict[str, object]:
        messages = sorted(thread.messages, key=lambda message: (_datetime_sort_value(message.created_at), message.id))
        transcript = [
            {
                "id": message.id,
                "sender_type": message.sender_type,
                "label": "用户来信" if message.sender_type == "user" else ("咨询师回信" if message.sender_type == "counselor" else "AI回信"),
                "content": message.content,
                "created_at": message.created_at.isoformat(),
            }
            for message in messages
        ]
        latest_risk = next(
            (assessment for assessment in reversed(thread.risk_assessments) if assessment.target_type == "user_letter"),
            None,
        )
        return {
            "kind": "mail_thread_reply",
            "mail_thread_id": thread.id,
            "signature": thread.signature,
            "response_preference": "理性分析",
            "memory_summary": thread.memory.summary if thread.memory else "",
            "risk": {
                "level": latest_risk.risk_level if latest_risk is not None else "NONE",
                "signals": latest_risk.signals if latest_risk is not None else [],
                "reasoning": latest_risk.reasoning if latest_risk is not None else "",
            },
            "transcript": transcript,
            "instruction": (
                "请为咨询师生成一封可审阅修改后发送给用户的书信式回信。"
                "需要参考完整上下文和风险提示；不要声称自己是 AI；不要替代医疗诊断或治疗。"
            ),
        }

    def submit_counselor_reply(
        self,
        db: Session,
        counselor_id: str,
        thread_id: int,
        payload: CounselorThreadReplyRequest,
    ) -> MailThreadResponse | None:
        thread = db.scalar(
            select(MailThread).where(MailThread.id == thread_id, MailThread.assigned_counselor_id == counselor_id)
        )
        if thread is None:
            return None
        db.add(
            MailMessage(
                thread_id=thread.id,
                sender_type="counselor",
                sender_id=counselor_id,
                content=payload.content,
                status="sent",
            )
        )
        db.flush()
        reply_assessment = self.safety_service.assess_reply(payload.content)
        latest_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
        self._record_risk(
            db,
            thread.user_id,
            thread.id,
            latest_message.id if latest_message else None,
            "counselor_reply",
            reply_assessment,
        )
        thread.status = "waiting_user"
        db.commit()
        self.rebuild_memory(db, thread.id)
        refreshed = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
        )
        return MailThreadResponse.model_validate(refreshed) if refreshed is not None else None

    def submit_counselor_reply_text(
        self,
        db: Session,
        counselor_id: str,
        thread_id: int,
        content: str,
    ) -> MailThreadResponse | None:
        return self.submit_counselor_reply(
            db=db,
            counselor_id=counselor_id,
            thread_id=thread_id,
            payload=CounselorThreadReplyRequest(content=content),
        )

    def rebuild_memory(self, db: Session, thread_id: int) -> None:
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
        )
        if thread is None:
            return
        messages = sorted(thread.messages, key=lambda message: (_datetime_sort_value(message.created_at), message.id))
        summary = self._summarize(thread, messages)
        if thread.memory is None:
            thread.memory = ConversationMemory(
                thread_id=thread.id,
                user_id=thread.user_id,
                summary=summary,
                message_count=len(messages),
            )
            db.add(thread.memory)
        else:
            thread.memory.summary = summary
            thread.memory.message_count = len(messages)
        db.commit()

    def _pick_counselor(self, db: Session) -> str:
        if not self.settings.counselor_features_enabled:
            raise ValueError("当前暂未开放咨询师人工回复")
        counselor_usernames = self._active_counselor_usernames(db)
        if not counselor_usernames:
            raise ValueError("当前没有白名单内咨询师可以接收人工来信")
        return random.choice(counselor_usernames)

    def _pick_counselor_or_none(self, db: Session) -> str | None:
        if not self.settings.counselor_features_enabled:
            return None
        counselor_usernames = self._active_counselor_usernames(db)
        return random.choice(counselor_usernames) if counselor_usernames else None

    def _active_counselor_usernames(self, db: Session) -> list[str]:
        query = select(Account.username).where(Account.role == "counselor")
        if self.settings.active_counselor_ids:
            query = query.where(Account.username.in_(self.settings.active_counselor_ids))
        return list(db.scalars(query).all())

    async def _generate_ai_reply(self, thread: MailThread, latest_user_content: str, fallback_preference: str) -> str:
        if self.orchestration_service is None:
            raise ValueError("AI reply generation is not configured")
        preference = "理性分析"
        persona_name = self._persona_for_preference(preference)
        context_input = self._build_ai_generation_input(thread=thread, latest_user_content=latest_user_content, preference=preference)
        drafts = await self.orchestration_service.generate_all(
            user_input=context_input,
            persona_names=[persona_name],
            compare_sources=False,
            source_mode="auto",
            audience="user",
        )
        if not drafts:
            raise ValueError("AI 暂时没有生成回信，请稍后再试")
        return str(drafts[0].get("response") or "").strip()

    async def generate_pending_ai_reply(self, db: Session, user_id: str, thread_id: int) -> None:
        thread = db.scalar(
            select(MailThread)
            .where(MailThread.id == thread_id, MailThread.user_id == user_id)
            .options(selectinload(MailThread.messages), selectinload(MailThread.memory), selectinload(MailThread.risk_assessments))
        )
        if thread is None or thread.status != "waiting_ai" or thread.reply_mode != "ai":
            return
        latest_user = next(
            (message for message in reversed(sorted(thread.messages, key=lambda item: (_datetime_sort_value(item.created_at), item.id))) if message.sender_type == "user"),
            None,
        )
        if latest_user is None:
            return
        try:
            reply_text = await self._generate_ai_reply(
                thread=thread,
                latest_user_content=latest_user.content,
                fallback_preference=thread.response_preference,
            )
            self._append_ai_reply(db=db, thread=thread, reply_text=reply_text)
            db.commit()
            self.rebuild_memory(db, thread.id)
        except Exception:
            thread.status = "waiting_ai"
            db.commit()

    def _append_ai_reply(self, db: Session, thread: MailThread, reply_text: str) -> None:
        reply_text = self._with_ai_signature(reply_text)
        reply_assessment = self.safety_service.assess_reply(reply_text)
        if RISK_ORDER[reply_assessment.risk_level] >= RISK_ORDER["HIGH"]:
            reply_text = self.safety_service.safe_fallback_reply(
                counselor_available=self.settings.counselor_features_enabled
            )
            reply_text = self._with_ai_signature(reply_text)
            reply_assessment = self.safety_service.assess_reply(reply_text)
            if self.settings.counselor_features_enabled:
                thread.reply_mode = "human"
                thread.status = "waiting_counselor"
                if thread.assigned_counselor_id is None:
                    thread.assigned_counselor_id = self._pick_counselor_or_none(db)
            else:
                thread.status = "waiting_user"
        else:
            thread.status = "waiting_user"
        db.add(
            MailMessage(
                thread_id=thread.id,
                sender_type="ai",
                sender_id="mindful-ai",
                content=reply_text,
                status="sent",
            )
        )
        db.flush()
        ai_message = db.scalar(select(MailMessage).where(MailMessage.thread_id == thread.id).order_by(desc(MailMessage.id)))
        self._record_risk(db, thread.user_id, thread.id, ai_message.id if ai_message else None, "ai_reply", reply_assessment)

    def _with_ai_signature(self, reply_text: str) -> str:
        stripped = reply_text.strip()
        if not stripped:
            return stripped
        normalized_signature = f"——{AI_REPLY_SIGNATURE}"
        if AI_REPLY_SIGNATURE in stripped:
            return stripped
        return f"{stripped}\n\n{normalized_signature}"

    def _build_ai_generation_input(self, thread: MailThread, latest_user_content: str, preference: str) -> str:
        messages = sorted(thread.messages, key=lambda message: (_datetime_sort_value(message.created_at), message.id))
        transcript = "\n\n".join(
            f"{'用户来信' if message.sender_type == 'user' else ('咨询师回信' if message.sender_type == 'counselor' else 'AI既往回信')}：\n{message.content}"
            for message in messages[-6:]
        )
        memory = thread.memory.summary if thread.memory else ""
        return "\n\n".join(
            part
            for part in [
                f"【长期记忆摘要】\n{memory}" if memory else "",
                "【统一回应策略】理性分析",
                f"【用户署名】{thread.signature or '匿名'}",
                f"【最近书信往返】\n{transcript}" if transcript else "",
                f"【最新来信】\n{latest_user_content}",
                "请直接为用户写一封可发送的书信式 AI 回信。不要声称自己是 AI；不要替代医疗诊断或治疗。",
            ]
            if part
        )

    def _persona_for_preference(self, preference: str) -> str:
        return "理性破局教练"

    def _build_title(self, content: str) -> str:
        first_line = next((line.strip() for line in content.splitlines() if line.strip()), "")
        return (first_line[:28] + "...") if len(first_line) > 28 else first_line or "给心灵笔友的信"

    def _summarize(self, thread: MailThread, messages: list[MailMessage]) -> str:
        user_messages = [message.content for message in messages if message.sender_type == "user"]
        latest_user = user_messages[-1] if user_messages else ""
        first_user = user_messages[0] if user_messages else ""
        turns = len(user_messages)
        fragments = [
            f"这段书信共有 {len(messages)} 条消息，其中用户来信 {turns} 次。",
            "系统采用统一的理性分析回信策略。",
        ]
        risk_levels = [assessment.risk_level for assessment in thread.risk_assessments if assessment.target_type == "user_letter"]
        if first_user:
            fragments.append(f"起始困扰：{self._compact(first_user, 120)}")
        if latest_user and latest_user != first_user:
            fragments.append(f"最近一次来信重点：{self._compact(latest_user, 160)}")
        counselor_or_ai = [message.content for message in messages if message.sender_type in {"ai", "counselor"}]
        if counselor_or_ai:
            fragments.append(f"最近一次回信方向：{self._compact(counselor_or_ai[-1], 140)}")
        return "\n".join(fragments)

    def _compact(self, value: str, limit: int) -> str:
        cleaned = " ".join(value.split())
        return cleaned if len(cleaned) <= limit else f"{cleaned[:limit]}..."

    def _record_risk(
        self,
        db: Session,
        user_id: str,
        thread_id: int,
        message_id: int | None,
        target_type: str,
        assessment: SafetyAssessment,
    ) -> None:
        db.add(
            RiskAssessment(
                user_id=user_id,
                thread_id=thread_id,
                message_id=message_id,
                target_type=target_type,
                risk_level=assessment.risk_level,
                confidence=assessment.confidence,
                categories_json=assessment.categories,
                signals_json=assessment.signals,
                reasoning=assessment.reasoning,
                reviewed=False,
            )
        )

    def _previous_user_risk_levels(self, db: Session, user_id: str) -> list[str]:
        return list(
            db.scalars(
                select(RiskAssessment.risk_level)
                .where(RiskAssessment.user_id == user_id, RiskAssessment.target_type == "user_letter")
                .order_by(desc(RiskAssessment.created_at))
                .limit(5)
            ).all()
        )

    def _migrate_legacy_letters(self, db: Session, user_id: str) -> None:
        has_threads = db.scalar(select(func.count()).select_from(MailThread).where(MailThread.user_id == user_id)) or 0
        if has_threads:
            return
        letters = db.scalars(select(UserLetter).where(UserLetter.user_id == user_id).order_by(UserLetter.created_at)).all()
        if not letters:
            return
        for letter in letters:
            reply_mode = "human" if letter.reply_source == "human" else "ai"
            thread = MailThread(
                user_id=letter.user_id,
                signature=letter.signature,
                title=self._build_title(letter.letter_text),
                reply_mode=reply_mode,
                response_preference="理性分析",
                status="completed" if letter.status == "completed" else ("waiting_user" if letter.reply_text else "waiting_counselor"),
                assigned_counselor_id=letter.assigned_counselor_id,
                created_at=letter.created_at,
                updated_at=letter.updated_at,
            )
            db.add(thread)
            db.flush()
            db.add(
                MailMessage(
                    thread_id=thread.id,
                    sender_type="user",
                    sender_id=letter.user_id,
                    content=letter.letter_text,
                    status="sent",
                    created_at=letter.created_at,
                    updated_at=letter.created_at,
                )
            )
            if letter.reply_text:
                db.add(
                    MailMessage(
                        thread_id=thread.id,
                        sender_type="counselor" if reply_mode == "human" else "ai",
                        sender_id=letter.assigned_counselor_id or "mindful-ai",
                        content=letter.reply_text,
                        status="sent",
                        created_at=letter.updated_at,
                        updated_at=letter.updated_at,
                    )
                )
        db.commit()
        thread_ids = list(db.scalars(select(MailThread.id).where(MailThread.user_id == user_id)).all())
        for thread_id in thread_ids:
            self.rebuild_memory(db, thread_id)
