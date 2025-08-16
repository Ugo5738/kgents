from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProvisionRequest(BaseModel):
    """Input for natural-language agent provisioning.

    Minimal contract for conversation_service integration.
    """

    description: str = Field(..., description="Natural language task or agent description")
    project_hint: Optional[str] = Field(
        default=None, description="Optional project or workspace hint for scoping flows"
    )


class ProvisionResponse(BaseModel):
    """Response containing the selected/provisioned flow identifier."""

    flow_id: str = Field(..., description="Identifier of the Langflow flow to run")
    matched: bool = Field(
        default=True, description="Whether the selection matched the description heuristically"
    )
    source: str = Field(
        default="discovery",
        description="Where the flow selection came from (discovery|created|default)",
    )
    note: Optional[str] = Field(default=None, description="Optional informative note")
