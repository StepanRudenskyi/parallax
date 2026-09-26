package com.parallax.execution.backtest;

public record BacktestResult(
        String ticker,
        String strategyName,
        int barCount,
        int tradeCount,
        int positionCount,
        double netReturn,
        double maxDrawdown
) {
}