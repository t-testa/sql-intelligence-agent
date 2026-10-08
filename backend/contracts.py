from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Scalar = str | int | float | bool | None


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Parameter(Contract):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,31}$")
    value: str | int | float | bool | None


class Proposal(Contract):
    action: Literal["query", "clarify"]
    sql: str = Field(max_length=12000)
    parameters: list[Parameter] = Field(max_length=20)
    clarification: str = Field(max_length=1000)

    @model_validator(mode="after")
    def consistent(self) -> "Proposal":
        if self.action == "query" and (not self.sql.strip() or self.clarification):
            raise ValueError("Query proposals require SQL and no clarification")
        if self.action == "clarify" and (self.sql or self.parameters or not self.clarification):
            raise ValueError("Clarification proposals cannot contain executable SQL")
        return self


class QuestionRequest(Contract):
    question: str = Field(min_length=3, max_length=2000)
    conversation_id: str | None = Field(default=None, pattern=r"^[0-9a-f-]{36}$")


class SQLRequest(Contract):
    sql: str = Field(min_length=1, max_length=12000)
    parameters: list[Parameter] = Field(default_factory=list, max_length=20)


class PracticeRequest(SQLRequest):
    exercise_id: str = Field(min_length=1, max_length=64)


class ResultTable(Contract):
    columns: list[str]
    rows: list[list[Scalar]]
    row_count: int
    elapsed_ms: int
    truncated: bool = False


class Learning(Contract):
    grain: str
    concepts: list[str]
    explanation: list[str]
    cautions: list[str]
    exercise_id: str | None


class Answer(Contract):
    request_id: str
    conversation_id: str | None = None
    status: Literal["answered", "clarification"]
    answer: str
    sql: str | None = None
    parameters: list[Parameter] = Field(default_factory=list)
    result: ResultTable | None = None
    learning: Learning | None = None
