package com.parallax.execution.controller;

import com.parallax.execution.backtest.BacktestResult;
import com.parallax.execution.backtest.BacktestService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;
import java.util.NoSuchElementException;

@RestController
public class BacktestController {

    private final BacktestService backtestService;

    @Autowired
    public BacktestController(BacktestService backtestService) {
        this.backtestService = backtestService;
    }

    @GetMapping("/backtest/{ticker}")
    public ResponseEntity<?> backtest(@PathVariable String ticker) {
        try {
            BacktestResult result = backtestService.runQuantStrategy(ticker.toUpperCase());
            return ResponseEntity.ok(result);
        } catch (NoSuchElementException e) {
            return ResponseEntity.notFound().build();
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body(Map.of("error", e.getMessage()));
        }
    }
}