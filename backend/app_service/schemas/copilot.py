from pydantic import BaseModel, Field


class CopilotQuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class CopilotAnswerResponse(BaseModel):
    answer: str
    grounded_in: list[str]
    source: str
    intent: str
