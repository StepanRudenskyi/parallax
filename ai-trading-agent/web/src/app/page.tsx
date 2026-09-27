"use client";

import { useState } from "react";
import type { AnalyzeResponse, Verdict } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const verdictStyles: Record<Verdict, string> = {
  BUY: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
  HOLD: "bg-amber-500/10 text-amber-400 border-amber-500/30",
  SELL: "bg-rose-500/10 text-rose-400 border-rose-500/30",
};

function VerdictBadge({ verdict }: { verdict: Verdict }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-3 py-1 text-sm font-semibold ${verdictStyles[verdict]}`}
    >
      {verdict}
    </span>
  );
}

function ConfidenceBar({ confidence }: { confidence: number }) {
  return (
    <div className="mt-2 h-1.5 w-full rounded-full bg-neutral-800">
      <div
        className="h-1.5 rounded-full bg-neutral-400"
        style={{ width: `${Math.round(confidence * 100)}%` }}
      />
    </div>
  );
}

export default function Home() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);

  async function handleAnalyze() {
    if (!ticker.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker: ticker.trim().toUpperCase() }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Request failed (${res.status})`);
      }

      const data: AnalyzeResponse = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  const opinions = result
    ? [
        { name: "Quant", opinion: result.agent_opinions.quant },
        { name: "Sentiment", opinion: result.agent_opinions.sentiment },
        { name: "Fundamental", opinion: result.agent_opinions.fundamental },
      ]
    : [];

  return (
    <main className="min-h-screen bg-neutral-950 text-neutral-100">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <h1 className="text-2xl font-semibold tracking-tight">
          AI Trading Research Agent
        </h1>
        <p className="mt-1 text-sm text-neutral-400">
          Multi-agent analysis, synthesized by a supervisor, with historical
          strategy context.
        </p>

        <div className="mt-8 flex gap-3">
          <input
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAnalyze()}
            placeholder="AAPL"
            className="flex-1 rounded-lg border border-neutral-800 bg-neutral-900 px-4 py-2.5 text-sm outline-none placeholder:text-neutral-500 focus:border-neutral-600"
          />
          <button
            onClick={handleAnalyze}
            disabled={loading || !ticker.trim()}
            className="rounded-lg bg-neutral-100 px-5 py-2.5 text-sm font-medium text-neutral-900 transition disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading ? "Analyzing…" : "Analyze"}
          </button>
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
            {error}
          </p>
        )}

        {result && (
          <div className="mt-10 space-y-6">
            <section className="rounded-xl border border-neutral-800 bg-neutral-900/50 p-6">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-medium text-neutral-400">
                  Final Recommendation — {result.ticker}
                </h2>
                <VerdictBadge verdict={result.final_recommendation.final_verdict} />
              </div>
              <p className="mt-3 text-sm leading-relaxed text-neutral-200">
                {result.final_recommendation.summary}
              </p>
              <ConfidenceBar confidence={result.final_recommendation.confidence} />
              <p className="mt-1 text-xs text-neutral-500">
                Confidence: {Math.round(result.final_recommendation.confidence * 100)}%
              </p>
            </section>

            <section className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              {opinions.map(({ name, opinion }) => (
                <div
                  key={name}
                  className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-4"
                >
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-medium uppercase tracking-wide text-neutral-500">
                      {name}
                    </h3>
                    <VerdictBadge verdict={opinion.verdict} />
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-neutral-400">
                    {opinion.reasoning}
                  </p>
                  <ConfidenceBar confidence={opinion.confidence} />
                </div>
              ))}
            </section>

            {result.backtest_context && (
              <section className="rounded-xl border border-neutral-800 bg-neutral-900/30 p-6">
                <h2 className="text-sm font-medium text-neutral-400">
                  Backtest Context (historical strategy performance)
                </h2>
                {result.backtest_context.error ? (
                  <p className="mt-2 text-xs text-neutral-500">
                    {result.backtest_context.error}
                  </p>
                ) : (
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                    <Stat
                      label="Net return"
                      value={
                        result.backtest_context.netReturn !== undefined
                          ? `${((result.backtest_context.netReturn - 1) * 100).toFixed(1)}%`
                          : "—"
                      }
                    />
                    <Stat
                      label="Max drawdown"
                      value={
                        result.backtest_context.maxDrawdown !== undefined
                          ? `${(result.backtest_context.maxDrawdown * 100).toFixed(1)}%`
                          : "—"
                      }
                    />
                    <Stat
                      label="Positions"
                      value={result.backtest_context.positionCount?.toString() ?? "—"}
                    />
                    <Stat
                      label="Period"
                      value={
                        result.backtest_context.startDate && result.backtest_context.endDate
                          ? `${result.backtest_context.startDate} → ${result.backtest_context.endDate}`
                          : "—"
                      }
                    />
                  </div>
                )}
              </section>
            )}
          </div>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="mt-0.5 font-medium text-neutral-200">{value}</p>
    </div>
  );
}