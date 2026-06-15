from pydantic import BaseModel, Field, field_validator


class AgentQueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=500,
        description="需要 Agent 分析的自然语言问题。",
        examples=["统计各部门接口调用失败率，并生成分析报告"],
    )

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        question = value.strip()
        if not question:
            raise ValueError("问题不能为空。")
        return question
