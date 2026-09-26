from typing import TypedDict, Optional

from schemas import AgentOpinion, FinalRecommendation


class ResearchState(TypedDict):
    ticker: str
    quant_opinion: Optional[AgentOpinion]
    sentiment_opinion: Optional[AgentOpinion]
    fundamental_opinion: Optional[AgentOpinion]
    final_recommendation: Optional[FinalRecommendation]
