from datetime import datetime

from sqlalchemy import JSON, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_name: Mapped[str] = mapped_column(String(63), unique=True)
    module: Mapped[str] = mapped_column(String(63))
    kind: Mapped[str] = mapped_column(String(16), default="", server_default="")
    namespace: Mapped[str] = mapped_column(String(63))
    params: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ExamResult(Base):
    __tablename__ = "exam_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    detector: Mapped[str] = mapped_column(String(63))
    threat: Mapped[str] = mapped_column(String(32))
    exam: Mapped[str] = mapped_column(String(63))
    run_id: Mapped[int] = mapped_column(ForeignKey("runs.id"))
    state: Mapped[str] = mapped_column(String(16), default="running")
    flagged: Mapped[int | None]
    caught: Mapped[int | None]
    poisoned: Mapped[int | None]
    precision: Mapped[float | None] = mapped_column(Float)
    recall: Mapped[float | None] = mapped_column(Float)
    f1: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ImpactTest(Base):
    __tablename__ = "impact_tests"

    id: Mapped[int] = mapped_column(primary_key=True)
    suspect: Mapped[str] = mapped_column(String(63))
    clean: Mapped[str] = mapped_column(String(63))
    detector: Mapped[str] = mapped_column(String(63))
    state: Mapped[str] = mapped_column(String(16), default="running")
    step: Mapped[str] = mapped_column(String(120), default="")
    removed: Mapped[dict] = mapped_column(JSON, default=dict)
    results: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
