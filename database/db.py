import os
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from config import Config

logger = logging.getLogger("attendance_system.db")


class DatabaseManager:
    """
    Database connection and query manager.
    Supports MySQL as primary database with graceful SQLite fallback.
    """

    def __init__(self):
        self.engine_type = "unknown"
        self._mysql_module = None
        self._test_mysql()

    def _test_mysql(self):
        """Test if MySQL driver and connection are available."""
        if Config.DB_TYPE != "mysql":
            self.engine_type = "sqlite"
            return

        # Attempt to import mysql driver
        try:
            import mysql.connector
            self._mysql_module = ("mysql.connector", mysql.connector)
        except ImportError:
            try:
                import pymysql
                self._mysql_module = ("pymysql", pymysql)
            except ImportError:
                logger.warning("No MySQL Python driver found. Falling back to SQLite.")
                self.engine_type = "sqlite"
                return

        # Attempt test connection
        try:
            driver_name, driver = self._mysql_module
            if driver_name == "mysql.connector":
                # First connect to server without database to create if needed
                conn = driver.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    connection_timeout=3
                )
                cursor = conn.cursor()
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                conn.commit()
                cursor.close()
                conn.close()

                # Verify database connection
                conn = driver.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    database=Config.DB_NAME,
                    connection_timeout=3
                )
                conn.close()
            else:
                conn = driver.connect(
                    host=Config.DB_HOST,
                    port=Config.DB_PORT,
                    user=Config.DB_USER,
                    password=Config.DB_PASSWORD,
                    connect_timeout=3
                )
                with conn.cursor() as cursor:
                    cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{Config.DB_NAME}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
                conn.commit()
                conn.close()

            self.engine_type = "mysql"
            logger.info(f"Successfully connected to MySQL database: {Config.DB_NAME}@{Config.DB_HOST}")
        except Exception as e:
            logger.warning(
                f"MySQL connection failed ({e}). Falling back to SQLite at {Config.SQLITE_PATH} "
                "for seamless offline/local development."
            )
            self.engine_type = "sqlite"

    @contextmanager
    def get_connection(self):
        """Yield an active database connection and cursor, auto-closing on exit."""
        if self.engine_type == "mysql":
            driver_name, driver = self._mysql_module
            conn = None
            try:
                if driver_name == "mysql.connector":
                    conn = driver.connect(
                        host=Config.DB_HOST,
                        port=Config.DB_PORT,
                        user=Config.DB_USER,
                        password=Config.DB_PASSWORD,
                        database=Config.DB_NAME,
                        autocommit=False
                    )
                    cursor = conn.cursor(dictionary=True)
                else:
                    conn = driver.connect(
                        host=Config.DB_HOST,
                        port=Config.DB_PORT,
                        user=Config.DB_USER,
                        password=Config.DB_PASSWORD,
                        database=Config.DB_NAME,
                        cursorclass=driver.cursors.DictCursor,
                        autocommit=False
                    )
                    cursor = conn.cursor()
                yield conn, cursor
                conn.commit()
            except Exception as ex:
                if conn:
                    conn.rollback()
                logger.error(f"MySQL Error: {ex}")
                raise
            finally:
                if 'cursor' in locals() and cursor:
                    cursor.close()
                if conn and conn.is_connected() if hasattr(conn, 'is_connected') else conn:
                    conn.close()
        else:
            # SQLite connection
            Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(Config.SQLITE_PATH), timeout=10.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            try:
                yield conn, cursor
                conn.commit()
            except Exception as ex:
                conn.rollback()
                logger.error(f"SQLite Error: {ex}")
                raise
            finally:
                cursor.close()
                conn.close()

    def init_db(self):
        """Initialize tables and default seed data."""
        Config.init_app()
        self._test_mysql()

        with self.get_connection() as (conn, cursor):
            if self.engine_type == "mysql":
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(150) NOT NULL UNIQUE,
                        description TEXT NULL,
                        location VARCHAR(150) NULL DEFAULT 'Main Hall',
                        event_date DATE NOT NULL,
                        start_time TIME NULL,
                        end_time TIME NULL,
                        status VARCHAR(20) NOT NULL DEFAULT 'active',
                        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                        INDEX idx_event_date (event_date),
                        INDEX idx_event_status (status)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """)

                cursor.execute("""
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
                """)

                cursor.execute("""
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
                """)

                cursor.execute("""
                    INSERT IGNORE INTO events (name, description, location, event_date, start_time, end_time, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, ('Tech Fest 2026', 'Annual Technology and Innovation Festival', 'Campus Auditorium', datetime.now().strftime('%Y-%m-%d'), '09:00:00', '18:00:00', 'active'))

            else:
                # SQLite Schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE,
                        description TEXT,
                        location TEXT DEFAULT 'Main Hall',
                        event_date TEXT NOT NULL,
                        start_time TEXT,
                        end_time TEXT,
                        status TEXT DEFAULT 'active',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS participants (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        participant_uuid TEXT NOT NULL UNIQUE,
                        name TEXT NOT NULL,
                        registration_number TEXT NOT NULL UNIQUE,
                        email TEXT,
                        phone TEXT,
                        event_name TEXT NOT NULL,
                        category TEXT DEFAULT 'Participant',
                        qr_code_path TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS attendance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        participant_id INTEGER NOT NULL,
                        event_name TEXT NOT NULL,
                        entry_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                        exit_time TEXT,
                        status TEXT DEFAULT 'Present',
                        verification_method TEXT DEFAULT 'QR_SCAN',
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (participant_id) REFERENCES participants(id) ON DELETE CASCADE
                    );
                """)

                cursor.execute("SELECT id FROM events WHERE name = ?", ('Tech Fest 2026',))
                if not cursor.fetchone():
                    cursor.execute("""
                        INSERT INTO events (name, description, location, event_date, start_time, end_time, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, ('Tech Fest 2026', 'Annual Technology and Innovation Festival', 'Campus Auditorium', datetime.now().strftime('%Y-%m-%d'), '09:00:00', '18:00:00', 'active'))

        logger.info(f"Database initialized successfully using [{self.engine_type.upper()}] engine.")

    def query_all(self, sql: str, params: tuple = ()):
        """Execute query and return list of dictionaries."""
        with self.get_connection() as (conn, cursor):
            normalized_sql = sql if self.engine_type == "mysql" else sql.replace("%s", "?")
            cursor.execute(normalized_sql, params)
            rows = cursor.fetchall()
            if self.engine_type == "sqlite":
                return [dict(row) for row in rows]
            return rows

    def query_one(self, sql: str, params: tuple = ()):
        """Execute query and return single dictionary or None."""
        with self.get_connection() as (conn, cursor):
            normalized_sql = sql if self.engine_type == "mysql" else sql.replace("%s", "?")
            cursor.execute(normalized_sql, params)
            row = cursor.fetchone()
            if row and self.engine_type == "sqlite":
                return dict(row)
            return row

    def execute_write(self, sql: str, params: tuple = ()) -> int:
        """Execute insert/update/delete and return lastrowid or affected rows."""
        with self.get_connection() as (conn, cursor):
            normalized_sql = sql if self.engine_type == "mysql" else sql.replace("%s", "?")
            cursor.execute(normalized_sql, params)
            last_id = cursor.lastrowid
            return last_id


# Global Database Singleton
db = DatabaseManager()
