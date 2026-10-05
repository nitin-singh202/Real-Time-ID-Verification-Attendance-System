from typing import Optional, List, Dict, Any
from database.db import db


class Attendance:
    """Attendance model for recording and querying entrance/exit logs."""

    @classmethod
    def get_all(
        cls,
        event_name: str = "",
        date_filter: str = "",
        status_filter: str = "",
        search: str = ""
    ) -> List[Dict[str, Any]]:
        """Query attendance logs with comprehensive filters."""
        sql = """
            SELECT a.id, a.participant_id, a.event_name, a.entry_time, a.exit_time, a.status,
                   a.verification_method, a.created_at,
                   p.name, p.registration_number, p.email, p.category
            FROM attendance a
            JOIN participants p ON a.participant_id = p.id
            WHERE 1=1
        """
        params = []

        if event_name and event_name != "all":
            sql += " AND a.event_name = %s"
            params.append(event_name)

        if date_filter:
            sql += " AND DATE(a.entry_time) = %s"
            params.append(date_filter)

        if status_filter and status_filter != "all":
            sql += " AND a.status = %s"
            params.append(status_filter)

        if search and search.strip():
            term = f"%{search.strip()}%"
            sql += " AND (p.name LIKE %s OR p.registration_number LIKE %s)"
            params.extend([term, term])

        sql += " ORDER BY a.entry_time DESC, a.id DESC"
        return db.query_all(sql, tuple(params))

    @classmethod
    def get_by_id(cls, attendance_id: int) -> Optional[Dict[str, Any]]:
        return db.query_one(
            """
            SELECT a.*, p.name, p.registration_number, p.email, p.category
            FROM attendance a
            JOIN participants p ON a.participant_id = p.id
            WHERE a.id = %s
            """,
            (attendance_id,)
        )

    @classmethod
    def delete(cls, attendance_id: int) -> None:
        db.execute_write("DELETE FROM attendance WHERE id = %s", (attendance_id,))
