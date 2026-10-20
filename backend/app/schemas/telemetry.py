from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class DecisionRule(BaseModel):
    rule: str = Field(min_length=1, max_length=240)
    passed: bool


class SwitchDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    timestamp: datetime | None = None
    train_id: str | None = Field(default=None, max_length=64)
    switch_id: str | None = Field(default=None, max_length=64)
    position: float | None = None
    action: Literal["MAINTAIN", "SWITCH", "EMERGENCY_STOP"]
    action_level: str | None = Field(default=None, max_length=32)
    target_track: str | None = Field(default=None, max_length=80)
    confidence: float = Field(ge=0, le=1)
    rules_checked: list[DecisionRule] = Field(default_factory=list, max_length=64)
    raw_scores: dict[str, float | None] = Field(default_factory=dict)
    reason: str | None = Field(default=None, max_length=2000)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
