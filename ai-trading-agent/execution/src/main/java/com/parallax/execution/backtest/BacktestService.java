package com.parallax.execution.backtest;

import com.parallax.execution.exception.InstrumentNotFoundException;
import com.parallax.execution.exception.PriceDataNotFoundException;
import com.parallax.execution.model.BacktestResultEntity;
import com.parallax.execution.model.Instrument;
import com.parallax.execution.model.PriceBar;
import com.parallax.execution.repository.BacktestResultRepository;
import com.parallax.execution.repository.InstrumentRepository;
import com.parallax.execution.repository.PriceBarRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.ta4j.core.BarSeries;
import org.ta4j.core.Strategy;
import org.ta4j.core.TradingRecord;
import org.ta4j.core.backtest.BarSeriesManager;
import org.ta4j.core.criteria.drawdown.MaximumDrawdownCriterion;
import org.ta4j.core.criteria.pnl.NetReturnCriterion;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
public class BacktestService {

    private final InstrumentRepository instrumentRepository;
    private final PriceBarRepository priceBarRepository;
    private final BacktestResultRepository backtestResultRepository;

    public BacktestResult runQuantStrategy(String ticker, BacktestRequest request) {
        UUID recommendationId = extractRecommendationId(request);
        long start = System.currentTimeMillis();
        log.info("backtest started ticker={} recommendationId={}", ticker, recommendationId);

        try {
            Instrument instrument = instrumentRepository.findByTicker(ticker)
                    .orElseThrow(() -> new InstrumentNotFoundException(ticker));

            List<PriceBar> bars = priceBarRepository.findByInstrumentIdOrderByTsAsc(instrument.getId());
            if (bars.isEmpty()) {
                throw new PriceDataNotFoundException(ticker);
            }

            BarSeries series = BarSeriesConverter.toBarSeries(ticker, bars);
            Strategy strategy = QuantStrategyFactory.build(series);
            TradingRecord record = new BarSeriesManager(series).run(strategy);

            BacktestMetrics metrics = calculateMetrics(series, record);

            BacktestResultEntity saved = backtestResultRepository.save(
                    buildEntity(instrument, recommendationId, strategy, bars, series, metrics));

            long durationMs = System.currentTimeMillis() - start;
            log.info(
                    "backtest completed ticker={} durationMs={} netReturn={} maxDrawdown={} trades={}",
                    ticker, durationMs, metrics.netReturn(), metrics.maxDrawdown(), metrics.tradeCount()
            );

            return toResult(saved, ticker, strategy, series, metrics);
        } catch (Exception e) {
            long durationMs = System.currentTimeMillis() - start;
            log.error("backtest failed ticker={} durationMs={} error={}", ticker, durationMs, e.getMessage());
            throw e;
        }
    }

    private UUID extractRecommendationId(BacktestRequest request) {
        return request != null ? request.recommendationId() : null;
    }

    private BacktestMetrics calculateMetrics(BarSeries series, TradingRecord record) {
        double netReturn = new NetReturnCriterion().calculate(series, record).doubleValue();
        double maxDrawdown = new MaximumDrawdownCriterion().calculate(series, record).doubleValue();
        return new BacktestMetrics(netReturn, maxDrawdown, record.getTrades().size(), record.getPositionCount());
    }

    private BacktestResultEntity buildEntity(Instrument instrument, UUID recommendationId, Strategy strategy,
                                             List<PriceBar> bars, BarSeries series, BacktestMetrics metrics) {
        BacktestResultEntity entity = new BacktestResultEntity();
        entity.setId(UUID.randomUUID());
        entity.setInstrumentId(instrument.getId());
        entity.setRecommendationId(recommendationId); // null for standalone runs, set when triggered by Python
        entity.setStrategyName(strategy.getName());
        entity.setStartDate(bars.get(0).getTs().toLocalDate());
        entity.setEndDate(bars.get(bars.size() - 1).getTs().toLocalDate());
        entity.setBarCount(series.getBarCount());
        entity.setNumTrades(metrics.tradeCount());
        entity.setPositionCount(metrics.positionCount());
        entity.setPnlPercent(toBigDecimal((metrics.netReturn() - 1.0) * 100.0));
        entity.setMaxDrawdown(toBigDecimal(metrics.maxDrawdown()));
        return entity;
    }

    private BacktestResult toResult(BacktestResultEntity saved, String ticker, Strategy strategy,
                                    BarSeries series, BacktestMetrics metrics) {
        return new BacktestResult(
                saved.getId(),
                ticker,
                strategy.getName(),
                saved.getStartDate(),
                saved.getEndDate(),
                series.getBarCount(),
                metrics.tradeCount(),
                metrics.positionCount(),
                metrics.netReturn(),
                metrics.maxDrawdown()
        );
    }

    private static BigDecimal toBigDecimal(double value) {
        return BigDecimal.valueOf(value).setScale(6, RoundingMode.HALF_UP);
    }

    private record BacktestMetrics(double netReturn, double maxDrawdown, int tradeCount, int positionCount) {}
}