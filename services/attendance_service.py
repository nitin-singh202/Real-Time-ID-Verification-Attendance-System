import time
import logging
from datetime import datetime, date
from typing import Dict, Any, Tuple, Optional
from config import Config
from database.db import db
from services.excel_service import ExcelService

logger = logging.getLogger("attendance_system.attendance_service")


class AttendanceService:
    """Service handling attendance business logic, cooldowns, duplicate detection, and stats."""

    # In-memory cooldown dictionary: { registration_number: last_scan_epoch_time }
    _scan_cooldowns: Dict[str, float] = {}

    @classmethod
    def check_cooldown(cls, reg_no: str, cooldown_seconds: int = None) -> Tuple[bool, float]:
        """
        Check if the participant is in scan cooldown.
        Returns: (is_cooling_down, seconds_remaining)
        """
        if cooldown_seconds is None:
            cooldown_seconds = Config.QR_SCAN_COOLDOWN_SECONDS

        now = time.time()
        last_time = cls._scan_cooldowns.get(reg_no, 0)
        elapsed = now - last_time

        if elapsed < cooldown_seconds:
            return True, round(cooldown_seconds - elapsed, 1)

        # Update last scan time
        cls._scan_cooldowns[reg_no] = now
        return False, 0.0

    @classmethod
    def process_scan(
        cls,
        participant: Dict[str, Any],
        event_name: Optional[str] = None,
        verification_method: str = "QR_SCAN",
        is_exit_scan: bool = False
    ) -> Dict[str, Any]:
        """
        Process a verified participant scan, enforcing cooldown and duplicate prevention.
        """
        participant_id = participant["id"]
        reg_no = participant["registration_number"]
        name = participant["name"]
        assigned_event = participant.get("event_name") or "Tech Fest 2026"
        target_event = event_name if event_name else assigned_event

        # Check in-memory rapid-frame cooldown
        is_cooldown, remaining = cls.check_cooldown(reg_no)
        if is_cooldown:
            return {
                "success": True,
                "status": "COOLDOWN_IGNORED",
                "badge_status": "warning",
                "message": f"Scan acknowledged. Frame cooldown active ({remaining}s remaining).",
                "participant": participant,
                "entry_time": None
            }

        today_str = date.today().strftime("%Y-%m-%d")

        # Check if participant already has an attendance record for this event today
        existing = db.query_one(
            """
            SELECT * FROM attendance
            WHERE participant_id = %s AND event_name = %s AND DATE(entry_time) = %s
            ORDER BY id DESC LIMIT 1
            """,
            (participant_id, target_event, today_str)
        )

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if not existing:
            # First scan for this session -> Mark Present Entry
            attendance_id = db.execute_write(
                """
                INSERT INTO attendance (participant_id, event_name, entry_time, status, verification_method)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (participant_id, target_event, now_str, "Present", verification_method)
            )

            attendance_data = {
                "id": attendance_id,
                "participant_id": participant_id,
                "event_name": target_event,
                "entry_time": now_str,
                "exit_time": None,
                "status": "Present",
                "verification_method": verification_method
            }

            # Auto sync to Excel
            if Config.EXCEL_AUTO_SYNC:
                ExcelService.sync_to_master(participant, attendance_data)

            logger.info(f"Attendance recorded for {name} ({reg_no}) at {now_str}")
            return {
                "success": True,
                "status": "VERIFIED_NEW",
                "badge_status": "success",
                "message": "✓ Attendance marked successfully.",
                "participant": participant,
                "entry_time": now_str,
                "exit_time": None,
                "event_name": target_event
            }

        else:
            # Participant already scanned today
            entry_time_val = str(existing.get("entry_time", ""))
            exit_time_val = existing.get("exit_time")

            # Check if this is an Exit scan request
            if is_exit_scan or (Config.ALLOW_EXIT_SCAN and not exit_time_val):
                # Calculate time since entry
                try:
                    entry_dt = datetime.strptime(str(entry_time_val).split(".")[0], "%Y-%m-%d %H:%M:%S")
                    minutes_since_entry = (datetime.now() - entry_dt).total_seconds() / 60.0
                except Exception:
                    minutes_since_entry = 999.0

                # If more than 1 minute passed and exit scan is requested, record exit
                if minutes_since_entry >= 1.0 and is_exit_scan:
                    db.execute_write(
                        """
                        UPDATE attendance
                        SET exit_time = %s, updated_at = %s
                        WHERE id = %s
                        """,
                        (now_str, now_str, existing["id"])
                    )

                    existing["exit_time"] = now_str
                    if Config.EXCEL_AUTO_SYNC:
                        ExcelService.sync_to_master(participant, existing)

                    logger.info(f"Exit recorded for {name} ({reg_no}) at {now_str}")
                    return {
                        "success": True,
                        "status": "EXIT_RECORDED",
                        "badge_status": "info",
                        "message": "✓ Exit recorded successfully.",
                        "participant": participant,
                        "entry_time": entry_time_val,
                        "exit_time": now_str,
                        "event_name": target_event
                    }

            # Return Already Verified (Duplicate scan prevented)
            return {
                "success": True,
                "status": "ALREADY_VERIFIED",
                "badge_status": "warning",
                "message": f"✓ Already marked present at {entry_time_val}.",
                "participant": participant,
                "entry_time": entry_time_val,
                "exit_time": exit_time_val,
                "event_name": target_event
            }

    @classmethod
    def get_dashboard_metrics(cls, event_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculate live metrics for the admin dashboard."""
        today_str = date.today().strftime("%Y-%m-%d")

        if event_name and event_name != "all":
            total_reg = db.query_one(
                "SELECT COUNT(*) as count FROM participants WHERE event_name = %s", (event_name,)
            )["count"]

            present_count = db.query_one(
                """
                SELECT COUNT(DISTINCT a.participant_id) as count
                FROM attendance a
                WHERE a.event_name = %s AND DATE(a.entry_time) = %s AND a.status = 'Present'
                """,
                (event_name, today_str)
            )["count"]

            recent_scans = db.query_all(
                """
                SELECT a.id, a.entry_time, a.exit_time, a.status, a.verification_method,
                       p.name, p.registration_number, p.category, a.event_name
                FROM attendance a
                JOIN participants p ON a.participant_id = p.id
                WHERE a.event_name = %s
                ORDER BY a.entry_time DESC
                LIMIT 10
                """,
                (event_name,)
            )
        else:
            total_reg = db.query_one("SELECT COUNT(*) as count FROM participants")["count"]
            present_count = db.query_one(
                """
                SELECT COUNT(DISTINCT participant_id) as count
                FROM attendance
                WHERE DATE(entry_time) = %s AND status = 'Present'
                """,
                (today_str,)
            )["count"]

            recent_scans = db.query_all(
                """
                SELECT a.id, a.entry_time, a.exit_time, a.status, a.verification_method,
                       p.name, p.registration_number, p.category, a.event_name
                FROM attendance a
                JOIN participants p ON a.participant_id = p.id
                ORDER BY a.entry_time DESC
                LIMIT 10
                """
            )

        absent_count = max(0, total_reg - present_count)
        percentage = round((present_count / total_reg * 100), 1) if total_reg > 0 else 0.0

        today_entries = db.query_one(
            "SELECT COUNT(*) as count FROM attendance WHERE DATE(entry_time) = %s", (today_str,)
        )["count"]

        return {
            "total_registered": total_reg,
            "present_count": present_count,
            "absent_count": absent_count,
            "attendance_percentage": percentage,
            "today_entries": today_entries,
            "recent_scans": recent_scans
        }
