package com.parallax.execution.backtest;

import com.parallax.execution.model.Instrument;
import com.parallax.execution.model.PriceBar;
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

import java.util.List;
import java.util.NoSuchElementException;

@Service
public class BacktestService {

    private final InstrumentRepository instrumentRepository;
    private final PriceBarRepository priceBarRepository;

    @Autowired
    public BacktestService(InstrumentRepository instrumentRepository,
                           PriceBarRepository priceBarRepository) {
        this.instrumentRepository = instrumentRepository;
        this.priceBarRepository = priceBarRepository;
    }

    public BacktestResult runQuantStrategy(String ticker) {
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

        return new BacktestResult(
                ticker,
                strategy.getName(),
                series.getBarCount(),
                record.getTrades().size(),
                record.getPositionCount(),
                netReturn,
                maxDrawdown
        );
    }
}