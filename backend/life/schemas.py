from datetime import date, datetime
from typing import Literal, Any
from pydantic import BaseModel, Field, ConfigDict, model_validator

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")

class Login(Strict):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)

class RecordIn(Strict):
    kind: Literal["project", "task", "event", "service", "course", "study", "note", "custom_type", "custom"]
    title: str = Field(min_length=1, max_length=250)
    data: dict[str, Any] = Field(default_factory=dict)

class RecordUpdate(Strict):
    version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=250)
    data: dict[str, Any]

class Project(Strict):
    status: Literal["idea", "active", "paused", "done"] = "idea"
    description: str = Field(default="", max_length=20000)

class Task(Strict):
    status: Literal["todo", "doing", "done"] = "todo"
    due: date | None = None
    planned_minutes: int = Field(default=0, ge=0, le=10080)

class Event(Strict):
    start: datetime
    end: datetime
    icon: str = Field(default="calendar", max_length=40)
    @model_validator(mode="after")
    def valid(self):
        if self.start.utcoffset() is None or self.end.utcoffset() is None or self.end <= self.start:
            raise ValueError("Use timezone-aware start/end, with end after start")
        return self

class Service(Strict):
    provider: str = Field(default="", max_length=200)
    category: Literal["server", "sim", "subscription", "other"] = "other"
    details: dict[str, str] = Field(default_factory=dict)
    amount_minor: int = Field(gt=0, le=10**15, strict=True)
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3}$")
    first_due: date
    repeat: Literal["once", "days", "monthly", "yearly"]
    interval: int = Field(default=1, ge=1, le=366)
    active: bool = True
    provider_balance_minor: int | None = None

class Course(Strict):
    steps: list[str] = Field(min_length=1, max_length=1000)
    @model_validator(mode="after")
    def unique(self):
        if len(set(self.steps)) != len(self.steps) or any(not s.strip() or len(s)>200 for s in self.steps):
            raise ValueError("Steps must be nonempty and unique")
        return self

class Study(Strict):
    course_id: str
    step: str
    start: datetime
    end: datetime
    evidence: str = Field(min_length=1, max_length=20000)
    @model_validator(mode="after")
    def valid(self):
        if self.start.utcoffset() is None or self.end.utcoffset() is None or self.end <= self.start:
            raise ValueError("Invalid study interval")
        return self

class Note(Strict):
    text: str = Field(default="", max_length=100000)

class CustomType(Strict):
    fields: dict[str, Literal["text", "integer", "boolean", "date"]] = Field(max_length=50)

class Custom(Strict):
    type_id: str
    values: dict[str, Any] = Field(max_length=50)

class AccountIn(Strict):
    name: str = Field(min_length=1, max_length=100)
    currency: str = Field(default="RUB", pattern=r"^[A-Z]{3}$")
    opening_minor: int = Field(default=0, ge=-10**15, le=10**15, strict=True)

class OperationIn(Strict):
    key: str = Field(min_length=1, max_length=100)
    kind: Literal["income", "expense", "transfer", "loan_received", "loan_repayment"]
    account_id: str
    target_id: str | None = None
    amount_minor: int = Field(gt=0, le=10**15, strict=True)
    occurred_at: datetime
    title: str = Field(min_length=1, max_length=250)
    record_id: str | None = None
    @model_validator(mode="after")
    def valid(self):
        if self.occurred_at.utcoffset() is None: raise ValueError("Timezone required")
        if (self.kind == "transfer") != bool(self.target_id): raise ValueError("Target only for transfers")
        if self.target_id == self.account_id: raise ValueError("Accounts must differ")
        return self

class PayIn(Strict):
    account_id: str
    occurred_at: datetime
    @model_validator(mode="after")
    def valid(self):
        if self.occurred_at.utcoffset() is None: raise ValueError("Timezone required")
        return self

class LinkIn(Strict):
    source: str
    target: str
    relation: str = Field(min_length=1, max_length=80)
