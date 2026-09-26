package com.parallax.execution.backtest;

import java.time.LocalDate;
import java.util.UUID;

public record BacktestResult(
        UUID backtestResultId,
        String ticker,
        String strategyName,
        LocalDate startDate,
        LocalDate endDate,
        int barCount,
        int tradeCount,
        int positionCount,
        double netReturn,
        double maxDrawdown
) {
}