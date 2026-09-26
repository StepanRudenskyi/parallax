package com.parallax.execution.repository;

import com.parallax.execution.model.PriceBar;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;
import java.util.UUID;

public interface PriceBarRepository extends JpaRepository<PriceBar, Long> {
    List<PriceBar> findByInstrumentIdOrderByTsAsc(UUID instrumentId);

    long countByInstrumentId(UUID instrumentId);
}