-- ====================================================================
-- Real-Time ID Verification & Attendance System Database Schema
-- Compatible with MySQL 5.7+ / 8.0+
-- ====================================================================

CREATE DATABASE IF NOT EXISTS attendance_system
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE attendance_system;

-- --------------------------------------------------------------------
-- Table: events
-- Stores event / classroom / seminar / workshop configurations
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL UNIQUE,
    description TEXT NULL,
    location VARCHAR(150) NULL DEFAULT 'Main Hall',
    event_date DATE NOT NULL,
    start_time TIME NULL,
    end_time TIME NULL,
    status ENUM('active', 'upcoming', 'completed') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_event_date (event_date),
    INDEX idx_event_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- Table: participants
-- Stores registered participants with their unique registration numbers and UUIDs
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS participants (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participant_uuid VARCHAR(64) NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    registration_number VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(150) NULL,
    phone VARCHAR(50) NULL,
    event_name VARCHAR(150) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Participant',
    qr_code_path VARCHAR(255) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_participant_uuid (participant_uuid),
    INDEX idx_registration_number (registration_number),
    INDEX idx_event_name (event_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- Table: attendance
-- Stores entry and exit records for participants
-- --------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    participant_id INT NOT NULL,
    event_name VARCHAR(150) NOT NULL,
    entry_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    exit_time DATETIME NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Present',
    verification_method VARCHAR(50) NOT NULL DEFAULT 'QR_SCAN',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE,
    INDEX idx_participant_attendance (participant_id),
    INDEX idx_event_attendance (event_name),
    INDEX idx_entry_time (entry_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------------------
-- Default Seed Event
-- --------------------------------------------------------------------
INSERT IGNORE INTO events (name, description, location, event_date, start_time, end_time, status)
VALUES ('Tech Fest 2026', 'Annual Technology and Innovation Festival', 'Campus Auditorium', CURDATE(), '09:00:00', '18:00:00', 'active');
