from enum import Enum

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db import Base


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    MEMORY = "memory"


class Message(Base):
    __tablename__ = "message"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(
        Integer,
        ForeignKey("conversation.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(String(16), nullable=False)
    content = Column(Text, nullable=False)
    memory_text = Column(Text, nullable=True)
    embedding_768 = Column(Vector(768), nullable=True)
    is_embedded = Column(Boolean, nullable=False, default=False)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation = relationship(
        "Conversation", foreign_keys=[conversation_id], back_populates="messages"
    )

    __table_args__ = (
        Index(
            "idx_message_embedding",
            "embedding_768",
            postgresql_using="hnsw",
            postgresql_ops={"embedding_768": "vector_cosine_ops"},
        ),
        Index(
            "idx_message_conversation_created",
            "conversation_id",
            "created_at",
        ),
    )


class Conversation(Base):
    __tablename__ = "conversation"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    last_message_id = Column(
        Integer,
        ForeignKey(
            "message.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_conversation_last_message",
        ),
        nullable=True,
    )
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user = relationship("User", back_populates="conversations")
    last_message = relationship(
        "Message", foreign_keys=[last_message_id], uselist=False
    )
    messages = relationship(
        "Message",
        foreign_keys=[Message.conversation_id],
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="asc(Message.created_at)",
    )
