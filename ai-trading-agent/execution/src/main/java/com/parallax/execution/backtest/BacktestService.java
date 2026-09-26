package com.parallax.execution.backtest;

import com.parallax.execution.model.BacktestResultEntity;
import com.parallax.execution.model.Instrument;
import com.parallax.execution.model.PriceBar;
import com.parallax.execution.repository.BacktestResultRepository;
import com.parallax.execution.repository.InstrumentRepository;
import com.parallax.execution.repository.PriceBarRepository;
import org.springframework.beans.factory.annotation.Autowired;
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
import java.util.NoSuchElementException;
import java.util.UUID;

@Service
public class BacktestService {

    private final InstrumentRepository instrumentRepository;
    private final PriceBarRepository priceBarRepository;
    private final BacktestResultRepository backtestResultRepository;

    @Autowired
    public BacktestService(InstrumentRepository instrumentRepository,
                           PriceBarRepository priceBarRepository,
                           BacktestResultRepository backtestResultRepository) {
        this.instrumentRepository = instrumentRepository;
        this.priceBarRepository = priceBarRepository;
        this.backtestResultRepository = backtestResultRepository;
    }

    public BacktestResult runQuantStrategy(String ticker, UUID recommendationId) {
        Instrument instrument = instrumentRepository.findByTicker(ticker)
                .orElseThrow(() -> new NoSuchElementException("Instrument not found: " + ticker));

        List<PriceBar> bars = priceBarRepository.findByInstrumentIdOrderByTsAsc(instrument.getId());
        if (bars.isEmpty()) {
            throw new NoSuchElementException("No price bars found for: " + ticker);
        }

        BarSeries series = BarSeriesConverter.toBarSeries(ticker, bars);
        Strategy strategy = QuantStrategyFactory.build(series);

        TradingRecord record = new BarSeriesManager(series).run(strategy);

        double netReturn = new NetReturnCriterion().calculate(series, record).doubleValue();
        double maxDrawdown = new MaximumDrawdownCriterion().calculate(series, record).doubleValue();

        int tradeCount = record.getTrades().size();
        int positionCount = record.getPositionCount();

        BacktestResultEntity entity = new BacktestResultEntity();
        entity.setId(UUID.randomUUID());
        entity.setInstrumentId(instrument.getId());
        entity.setRecommendationId(recommendationId); // null for standalone runs, set when triggered by Python
        entity.setStrategyName(strategy.getName());
        entity.setStartDate(bars.get(0).getTs().toLocalDate());
        entity.setEndDate(bars.get(bars.size() - 1).getTs().toLocalDate());
        entity.setBarCount(series.getBarCount());
        entity.setNumTrades(tradeCount);
        entity.setPositionCount(positionCount);
        entity.setPnlPercent(toBigDecimal((netReturn - 1.0) * 100.0));
        entity.setMaxDrawdown(toBigDecimal(maxDrawdown));

        BacktestResultEntity saved = backtestResultRepository.save(entity);

        return new BacktestResult(
                saved.getId(),
                ticker,
                strategy.getName(),
                saved.getStartDate(),
                saved.getEndDate(),
                series.getBarCount(),
                tradeCount,
                positionCount,
                netReturn,
                maxDrawdown
        );
    }

    private static BigDecimal toBigDecimal(double value) {
        return BigDecimal.valueOf(value).setScale(6, RoundingMode.HALF_UP);
    }
}