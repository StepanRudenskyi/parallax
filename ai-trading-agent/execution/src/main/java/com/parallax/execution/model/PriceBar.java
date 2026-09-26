package com.parallax.execution.model;

import jakarta.persistence.*;
import java.math.BigDecimal;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "price_bar")
public class PriceBar {

    @Id
    private Long id;

    @Column(name = "instrument_id", nullable = false)
    private UUID instrumentId;

    @Column(nullable = false)
    private OffsetDateTime ts;

    // Same reasoning as Instrument.assetType — read-only, plain text mapping.
    @Column(nullable = false)
    private String timeframe;

    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private BigDecimal volume;

    @Column(nullable = false)
    private String source;

    public Long getId() { return id; }
    public UUID getInstrumentId() { return instrumentId; }
    public OffsetDateTime getTs() { return ts; }
    public String getTimeframe() { return timeframe; }
    public BigDecimal getOpen() { return open; }
    public BigDecimal getHigh() { return high; }
    public BigDecimal getLow() { return low; }
    public BigDecimal getClose() { return close; }
    public BigDecimal getVolume() { return volume; }
    public String getSource() { return source; }
}