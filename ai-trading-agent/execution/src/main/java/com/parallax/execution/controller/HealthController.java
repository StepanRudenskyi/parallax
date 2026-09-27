package com.parallax.execution.controller;

import com.parallax.execution.exception.InstrumentNotFoundException;
import com.parallax.execution.model.Instrument;
import com.parallax.execution.repository.InstrumentRepository;
import com.parallax.execution.repository.PriceBarRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequiredArgsConstructor
public class HealthController {

    private final InstrumentRepository instrumentRepository;
    private final PriceBarRepository priceBarRepository;

    @GetMapping("/health")
    public Map<String, String> health() {
        return Map.of("status", "ok");
    }

    /**
     * Phase 3 skeleton checkpoint: proves this Java service can read the same
     * Postgres data the Python layer wrote in Phase 0, over plain JDBC/JPA,
     * with ddl-auto=none (no schema ownership on this side).
     */
    @GetMapping("/health/db/{ticker}")
    public Map<String, Object> checkDb(@PathVariable String ticker) {
        Instrument instrument = instrumentRepository.findByTicker(ticker)
                .orElseThrow(() -> new InstrumentNotFoundException(ticker));
        long barCount = priceBarRepository.countByInstrumentId(instrument.getId());
        return Map.of(
                "ticker", instrument.getTicker(),
                "assetType", instrument.getAssetType(),
                "priceBarCount", barCount
        );
    }
}