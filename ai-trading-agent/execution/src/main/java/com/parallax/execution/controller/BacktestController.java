package com.parallax.execution.controller;

import com.parallax.execution.backtest.BacktestRequest;
import com.parallax.execution.backtest.BacktestResult;
import com.parallax.execution.backtest.BacktestService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequiredArgsConstructor
@RequestMapping("/backtest")
public class BacktestController {

    private final BacktestService backtestService;

    @PostMapping("/{ticker}")
    public ResponseEntity<BacktestResult> backtest(@PathVariable String ticker,
                                                   @RequestBody(required = false) BacktestRequest request) {
        return ResponseEntity.ok(backtestService.runQuantStrategy(ticker.toUpperCase(), request));
    }

    @GetMapping("/{ticker}")
    public ResponseEntity<BacktestResult> backtestGet(@PathVariable String ticker) {
        return backtest(ticker, null);
    }
}