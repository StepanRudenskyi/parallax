package com.parallax.execution.exception;

public class InstrumentNotFoundException extends RuntimeException {
    public InstrumentNotFoundException(String ticker) {
        super("Instrument not found: " + ticker);
    }
}