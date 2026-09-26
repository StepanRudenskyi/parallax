from pydantic import BaseModel, Field


class AgentOpinion(BaseModel):
    verdict: str = Field(description="One of: BUY, HOLD, SELL")
    confidence: float = Field(description="Confidence score between 0 and 1")
    reasoning: str = Field(description="Short explanation for the verdict")


class FinalRecommendation(BaseModel):
    final_verdict: str = Field(description="One of: BUY, HOLD, SELL")
    confidence: float = Field(description="Overall confidence score between 0 and 1")
    summary: str = Field(
        description="Short synthesis explaining how the three specialist opinions "
        "were weighted into the final verdict"
    )