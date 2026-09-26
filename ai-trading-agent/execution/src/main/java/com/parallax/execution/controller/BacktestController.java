package com.parallax.execution.controller;

import com.parallax.execution.backtest.BacktestRequest;
import com.parallax.execution.backtest.BacktestResult;
import com.parallax.execution.backtest.BacktestService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.NoSuchElementException;

@RestController
public class BacktestController {

    private final BacktestService backtestService;

    @Autowired
    public BacktestController(BacktestService backtestService) {
        this.backtestService = backtestService;
    }

    /**
     * Standalone backtest — no recommendation attached (backwards-compatible
     * with the Phase 3 skeleton: GET still works, body is optional).
     */
    @PostMapping("/backtest/{ticker}")
    public ResponseEntity<?> backtest(@PathVariable String ticker,
                                      @RequestBody(required = false) BacktestRequest request) {
        try {
            var recommendationId = request != null ? request.recommendationId() : null;
            BacktestResult result = backtestService.runQuantStrategy(ticker.toUpperCase(), recommendationId);
            return ResponseEntity.ok(result);
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        } catch (Exception e) {
            return ResponseEntity.internalServerError().body(Map.of("error", e.getMessage()));
        }
    }

    @GetMapping("/backtest/{ticker}")
    public ResponseEntity<?> backtestGet(@PathVariable String ticker) {
        return backtest(ticker, null);
    }
}