package com.parallax.execution.model;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

import java.util.UUID;

@Entity
@Table(name = "instrument")
public class Instrument {

    @Id
    private UUID id;

    @Column(nullable = false)
    private String ticker;

    // Read as plain text: Postgres returns the native enum's label as a
    // string on SELECT, and this service never INSERTs into this table
    // (Python/Alembic owns writes here) so we don't need enum write support.
    @Column(name = "asset_type", nullable = false)
    private String assetType;

    @Column(nullable = false)
    private String source;

    @Column(nullable = false)
    private String currency;

    @Column(name = "is_active", nullable = false)
    private boolean active;

    public UUID getId() { return id; }
    public String getTicker() { return ticker; }
    public String getAssetType() { return assetType; }
    public String getSource() { return source; }
    public String getCurrency() { return currency; }
    public boolean isActive() { return active; }
}