package com.parallax.execution.exception;

public class PriceDataNotFoundException extends RuntimeException {
    public PriceDataNotFoundException(String ticker) {
        super("No price bars found for: " + ticker);
    }
}