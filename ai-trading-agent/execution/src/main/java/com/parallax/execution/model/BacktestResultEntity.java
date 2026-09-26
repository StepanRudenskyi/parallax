package com.parallax.execution.model;

import jakarta.persistence.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.util.UUID;

@Entity
@Table(name = "backtest_result")
public class BacktestResultEntity {

    @Id
    private UUID id;

    @Column(name = "instrument_id", nullable = false)
    private UUID instrumentId;

    @Column(name = "recommendation_id")
    private UUID recommendationId;

    @Column(name = "strategy_name", nullable = false)
    private String strategyName;

    @Column(name = "start_date")
    private LocalDate startDate;

    @Column(name = "end_date")
    private LocalDate endDate;

    @Column(name = "bar_count")
    private Integer barCount;

    @Column(name = "num_trades")
    private Integer numTrades;

    @Column(name = "position_count")
    private Integer positionCount;

    @Column(name = "pnl_percent")
    private BigDecimal pnlPercent;

    @Column(name = "max_drawdown")
    private BigDecimal maxDrawdown;

    @Column(name = "sharpe_ratio")
    private BigDecimal sharpeRatio;

    @Column(name = "executed_at", insertable = false, updatable = false)
    private OffsetDateTime executedAt;

    public UUID getId() { return id; }
    public void setId(UUID id) { this.id = id; }

    public UUID getInstrumentId() { return instrumentId; }
    public void setInstrumentId(UUID instrumentId) { this.instrumentId = instrumentId; }

    public UUID getRecommendationId() { return recommendationId; }
    public void setRecommendationId(UUID recommendationId) { this.recommendationId = recommendationId; }

    public String getStrategyName() { return strategyName; }
    public void setStrategyName(String strategyName) { this.strategyName = strategyName; }

    public LocalDate getStartDate() { return startDate; }
    public void setStartDate(LocalDate startDate) { this.startDate = startDate; }

    public LocalDate getEndDate() { return endDate; }
    public void setEndDate(LocalDate endDate) { this.endDate = endDate; }

    public Integer getBarCount() { return barCount; }
    public void setBarCount(Integer barCount) { this.barCount = barCount; }

    public Integer getNumTrades() { return numTrades; }
    public void setNumTrades(Integer numTrades) { this.numTrades = numTrades; }

    public Integer getPositionCount() { return positionCount; }
    public void setPositionCount(Integer positionCount) { this.positionCount = positionCount; }

    public BigDecimal getPnlPercent() { return pnlPercent; }
    public void setPnlPercent(BigDecimal pnlPercent) { this.pnlPercent = pnlPercent; }

    public BigDecimal getMaxDrawdown() { return maxDrawdown; }
    public void setMaxDrawdown(BigDecimal maxDrawdown) { this.maxDrawdown = maxDrawdown; }

    public BigDecimal getSharpeRatio() { return sharpeRatio; }
    public void setSharpeRatio(BigDecimal sharpeRatio) { this.sharpeRatio = sharpeRatio; }

    public OffsetDateTime getExecutedAt() { return executedAt; }
}