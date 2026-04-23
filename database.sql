CREATE DATABASE IF NOT EXISTS `project_api_quangdev`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE `project_api_quangdev`;

CREATE TABLE IF NOT EXISTS `admin_users` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `username` VARCHAR(120) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_admin_users_username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `api_keys` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(120) NOT NULL,
  `key_value` VARCHAR(255) NOT NULL,
  `note` VARCHAR(255) NULL,
  `rate_limit_per_minute` INT NOT NULL DEFAULT 100,
  `is_active` TINYINT(1) NOT NULL DEFAULT 1,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_api_keys_name` (`name`),
  UNIQUE KEY `uq_api_keys_key_value` (`key_value`),
  KEY `idx_api_keys_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `api_logs` (
  `id` BIGINT NOT NULL AUTO_INCREMENT,
  `method` VARCHAR(16) NOT NULL,
  `path` VARCHAR(255) NOT NULL,
  `status_code` INT NOT NULL,
  `processing_time_ms` FLOAT NOT NULL,
  `api_key` VARCHAR(255) NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_api_logs_created_at` (`created_at`),
  KEY `idx_api_logs_status_code` (`status_code`),
  KEY `idx_api_logs_path` (`path`),
  KEY `idx_api_logs_api_key` (`api_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
