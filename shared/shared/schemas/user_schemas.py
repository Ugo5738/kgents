from typing import List
from uuid import UUID

from pydantic import BaseModel, Field


class UserTokenData(BaseModel):
    """
    Defines the structure of the JWT payload after validation.
    This schema is the shared contract between the auth_service and all
    resource services.
    """

    user_id: UUID = Field(..., alias="sub")
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
