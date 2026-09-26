package com.parallax.execution.backtest;

import com.parallax.execution.model.PriceBar;
import org.ta4j.core.BarSeries;
import org.ta4j.core.BaseBarSeriesBuilder;

import java.time.Duration;
import java.util.List;

public class BarSeriesConverter {

    public static BarSeries toBarSeries(String name, List<PriceBar> bars) {
        BarSeries series = new BaseBarSeriesBuilder().withName(name).build();

        for (PriceBar bar : bars) {
            series.addBar(
                    series.barBuilder()
                            .timePeriod(Duration.ofDays(1))
                            .endTime(bar.getTs().toInstant())
                            .openPrice(bar.getOpen().doubleValue())
                            .highPrice(bar.getHigh().doubleValue())
                            .lowPrice(bar.getLow().doubleValue())
                            .closePrice(bar.getClose().doubleValue())
                            .volume(bar.getVolume() != null ? bar.getVolume().doubleValue() : 0.0)
                            .build()
            );
        }

        return series;
    }
}