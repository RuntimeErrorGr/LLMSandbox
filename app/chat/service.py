from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.models import ChatMessage
from app.llm.models import chat_model

HISTORY_LIMIT = 10

SYSTEM_PROMPT = (
    "You are the assistant of the LLM Sandbox, a platform that detects poisoning attacks "
    "(label flipping, clean-label backdoors) in LLM training data. Answer briefly and clearly."
)

prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)

chain = prompt | chat_model() | StrOutputParser()


def history(db: Session, limit: int | None = None) -> list[ChatMessage]:
    newest_first = select(ChatMessage).order_by(ChatMessage.id.desc()).limit(limit)
    return list(reversed(db.scalars(newest_first).all()))


def to_langchain(messages: list[ChatMessage]) -> list[BaseMessage]:
    return [
        HumanMessage(message.content) if message.role == "user" else AIMessage(message.content)
        for message in messages
    ]


def ask(db: Session, question: str) -> list[ChatMessage]:
    past = to_langchain(history(db, HISTORY_LIMIT))
    answer = chain.invoke({"history": past, "question": question})

    exchange = [
        ChatMessage(role="user", content=question),
        ChatMessage(role="assistant", content=answer),
    ]
    db.add_all(exchange)
    db.commit()
    return exchange


def clear(db: Session) -> None:
    db.execute(delete(ChatMessage))
    db.commit()
