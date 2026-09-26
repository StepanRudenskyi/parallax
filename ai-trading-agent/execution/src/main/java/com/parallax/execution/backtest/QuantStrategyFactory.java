package com.parallax.execution.backtest;

import org.ta4j.core.BarSeries;
import org.ta4j.core.BaseStrategy;
import org.ta4j.core.Rule;
import org.ta4j.core.Strategy;
import org.ta4j.core.indicators.RSIIndicator;
import org.ta4j.core.indicators.averages.SMAIndicator;
import org.ta4j.core.indicators.helpers.ClosePriceIndicator;
import org.ta4j.core.rules.CrossedDownIndicatorRule;
import org.ta4j.core.rules.CrossedUpIndicatorRule;
import org.ta4j.core.rules.OverIndicatorRule;
import org.ta4j.core.rules.UnderIndicatorRule;

/**
 * Deliberately mirrors the indicators used by the Python Quant Agent
 * (SMA-20, RSI-14) so both layers of the system reason about the same
 * signals, even though this strategy is independent of any specific
 * LLM-produced recommendation. Wiring a specific recommendation into a
 * targeted backtest is a follow-up step, not part of this first version.
 *
 * Entry: price crosses above SMA(20) AND RSI(14) is not already overbought.
 * Exit:  RSI(14) becomes overbought (>70) OR price crosses back below SMA(20).
 */
public class QuantStrategyFactory {

    public static Strategy build(BarSeries series) {
        ClosePriceIndicator closePrice = new ClosePriceIndicator(series);
        SMAIndicator sma20 = new SMAIndicator(closePrice, 20);
        RSIIndicator rsi14 = new RSIIndicator(closePrice, 14);

        Rule entryRule = new CrossedUpIndicatorRule(closePrice, sma20)
                .and(new UnderIndicatorRule(rsi14, series.numFactory().numOf(70)));

        Rule exitRule = new OverIndicatorRule(rsi14, series.numFactory().numOf(70))
                .or(new CrossedDownIndicatorRule(closePrice, sma20));

        Strategy strategy = new BaseStrategy("SMA20+RSI14 (mirrors Quant Agent)", entryRule, exitRule);
        strategy.setUnstableBars(20); // warm-up: SMA-20 needs 20 bars before it's meaningful
        return strategy;
    }
}