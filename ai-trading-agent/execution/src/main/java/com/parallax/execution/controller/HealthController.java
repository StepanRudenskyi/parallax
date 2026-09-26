package com.parallax.execution.controller;

import com.parallax.execution.model.Instrument;
import com.parallax.execution.repository.InstrumentRepository;
import com.parallax.execution.repository.PriceBarRepository;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
public class HealthController {

    private final InstrumentRepository instrumentRepository;
    private final PriceBarRepository priceBarRepository;

    @Autowired
    public HealthController(InstrumentRepository instrumentRepository,
                            PriceBarRepository priceBarRepository) {
        this.instrumentRepository = instrumentRepository;
        this.priceBarRepository = priceBarRepository;
    }

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
    public ResponseEntity<Map<String, Object>> checkDb(@PathVariable String ticker) {
        return instrumentRepository.findByTicker(ticker)
                .map(instrument -> {
                    long barCount = priceBarRepository.countByInstrumentId(instrument.getId());
                    return ResponseEntity.ok(Map.<String, Object>of(
                            "ticker", instrument.getTicker(),
                            "assetType", instrument.getAssetType(),
                            "priceBarCount", barCount
                    ));
                })
                .orElseGet(() -> ResponseEntity.notFound().build());
    }
}