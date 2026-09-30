from datetime import datetime

from pydantic import ConfigDict, Field
from pydantic.main import BaseModel

from app.schema.api import APIPaginationFilter
from app.schema.auth import UserSchema


class MessageSchema(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateMessageSchema(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    conversation_id: int | None = None


class ConversationPaginationFilter(APIPaginationFilter):
    pass


class ConversationSchema(BaseModel):
    id: int
    user: UserSchema
    last_message: MessageSchema | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
