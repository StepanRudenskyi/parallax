package com.parallax.execution.repository;

import com.parallax.execution.model.BacktestResultEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.UUID;

public interface BacktestResultRepository extends JpaRepository<BacktestResultEntity, UUID> {
}