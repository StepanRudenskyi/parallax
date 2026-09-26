package com.parallax.execution.repository;

import com.parallax.execution.model.Instrument;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;
import java.util.UUID;

public interface InstrumentRepository extends JpaRepository<Instrument, UUID> {
    Optional<Instrument> findByTicker(String ticker);
}