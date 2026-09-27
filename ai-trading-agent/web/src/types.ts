export type Verdict = "BUY" | "HOLD" | "SELL";

export interface AgentOpinion {
  verdict: Verdict;
  confidence: number;
  reasoning: string;
}

export interface FinalRecommendation {
  final_verdict: Verdict;
  confidence: number;
  summary: string;
}

export interface BacktestContext {
  backtestResultId?: string;
  strategyName?: string;
  startDate?: string;
  endDate?: string;
  barCount?: number;
  tradeCount?: number;
  positionCount?: number;
  netReturn?: number;
  maxDrawdown?: number;
  error?: string;
}

export interface AnalyzeResponse {
  analysis_run_id: string;
  recommendation_id: string;
  ticker: string;
  agent_opinions: {
    quant: AgentOpinion;
    sentiment: AgentOpinion;
    fundamental: AgentOpinion;
  };
  final_recommendation: FinalRecommendation;
  backtest_context: BacktestContext | null;
}