USE lottery;

CREATE TABLE IF NOT EXISTS raw_lottery_draws (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,
    source VARCHAR(50) NOT NULL,
    fetched_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    UNIQUE KEY uniq_period_source (period, source),
    INDEX idx_fetched_at (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lottery_draws (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period VARCHAR(50) NOT NULL UNIQUE,
    draw_time DATETIME NOT NULL,
    timestamp BIGINT NOT NULL,
    numbers JSON NOT NULL,
    sum INT,
    span INT,
    odd_even VARCHAR(10),
    big_small VARCHAR(10),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_draw_time (draw_time),
    INDEX idx_timestamp (timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS validation_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period VARCHAR(50) NOT NULL,
    check_item VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    detail JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_period (period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lottery_features (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    period VARCHAR(50) NOT NULL,
    feature_type VARCHAR(50) NOT NULL,
    schema_version INT NOT NULL DEFAULT 1,
    feature_value JSON NOT NULL,
    meta JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (period) REFERENCES lottery_draws(period),
    UNIQUE KEY uniq_period_type (period, feature_type),
    INDEX idx_period (period),
    INDEX idx_feature_type (feature_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_results (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    analysis_type VARCHAR(50) NOT NULL,
    schema_version INT NOT NULL DEFAULT 1,
    result_summary VARCHAR(255) NULL,
    result_data JSON NOT NULL,
    metadata JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_analysis_type (analysis_type),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS analysis_jobs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    job_type VARCHAR(50) NOT NULL,
    payload JSON NOT NULL,
    priority TINYINT NOT NULL DEFAULT 5,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    started_at DATETIME NULL,
    finished_at DATETIME NULL,
    result_id BIGINT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (result_id) REFERENCES analysis_results(id),
    INDEX idx_status (status),
    INDEX idx_job_type (job_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS collector_logs (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    source VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message VARCHAR(255) NOT NULL,
    detail JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_source (source),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pipeline_stats (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    component VARCHAR(50) NOT NULL,
    metric VARCHAR(50) NOT NULL,
    metric_value DOUBLE NOT NULL,
    detail JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_component_metric (component, metric),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS pipeline_alerts (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    component VARCHAR(50) NOT NULL,
    level VARCHAR(20) NOT NULL,
    message VARCHAR(255) NOT NULL,
    detail JSON NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_component_level (component, level),
    INDEX idx_alert_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
