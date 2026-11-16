from datetime import datetime

from sqlalchemy import JSON, String, Text, func
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
    namespace: Mapped[str] = mapped_column(String(63))
    params: Mapped[dict] = mapped_column(JSON)
    state: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
