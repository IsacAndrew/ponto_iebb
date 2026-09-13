"""Contratos da API: rejeitar dados inválidos antes das regras e do banco."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)


class LoginInput(Input):
    login: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=128)


class ScheduleInput(Input):
    effective: str
    days: dict[str, list[tuple[str, str]]] = Field(default_factory=dict)
    specific: bool = False
    reason: str = Field(default="Nova vigência", max_length=2000)


class PunchInput(Input):
    key: str = Field(min_length=1, max_length=100)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)
    overtime: bool = False
    forgot: Literal["yes", "no"] | None = None


class CorrectionInput(Input):
    person_id: int = Field(gt=0)
    date: str
    times: list[str] = Field(default_factory=list, max_length=48)
    reason: str = Field(min_length=1, max_length=2000)
