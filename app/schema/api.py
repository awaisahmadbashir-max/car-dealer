import math
from typing import Any

from pydantic import BaseModel, Field, computed_field, field_validator, model_serializer


class APIResponse(BaseModel):
    detail: str | None = Field(None, description="Detail")
    data: Any | None = Field(None, description="Data")
    extra: dict | None = Field(None, description="Extra data")

    @model_serializer(mode="wrap")
    def exclude_none_fields(self, handler: Any) -> dict:
        result = handler(self)
        return {k: v for k, v in result.items() if v is not None}

    @field_validator("data", mode="before")
    @classmethod
    def dump_models(cls, v: Any) -> Any:
        if isinstance(v, BaseModel):
            return v.model_dump()
        if isinstance(v, list):
            return [
                item.model_dump() if isinstance(item, BaseModel) else item for item in v
            ]
        return v


class APIPaginatedResponse(APIResponse):
    page: int = Field(1, description="Current page")
    limit: int = Field(10, description="Items per page")
    total_items: int = Field(0, description="Total items")

    @computed_field
    @property
    def total_pages(self) -> int:
        return math.ceil(self.total_items / self.limit) if self.limit > 0 else 0


class APIPaginationFilter(BaseModel):
    page: int = Field(1, ge=1, description="Current page")
    limit: int = Field(10, ge=1, le=100, description="Items per page")
