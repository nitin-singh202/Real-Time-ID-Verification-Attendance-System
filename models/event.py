from typing import Optional, List, Dict, Any
from database.db import db


class Event:
    """Event model representing classrooms, seminars, workshops, hackathons, etc."""

    def __init__(self, id=None, name="", description="", location="Main Hall", event_date="", start_time="09:00:00", end_time="17:00:00", status="active", created_at=None, updated_at=None):
        self.id = id
        self.name = name
        self.description = description
        self.location = location
        self.event_date = event_date
        self.start_time = start_time
        self.end_time = end_time
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at

    @classmethod
    def get_all(cls) -> List[Dict[str, Any]]:
        """Retrieve all events ordered by event_date desc."""
        return db.query_all("SELECT * FROM events ORDER BY event_date DESC, id DESC")

    @classmethod
    def get_by_id(cls, event_id: int) -> Optional[Dict[str, Any]]:
        return db.query_one("SELECT * FROM events WHERE id = %s", (event_id,))

    @classmethod
    def get_by_name(cls, name: str) -> Optional[Dict[str, Any]]:
        return db.query_one("SELECT * FROM events WHERE name = %s", (name,))

    @classmethod
    def get_active(cls) -> List[Dict[str, Any]]:
        return db.query_all("SELECT * FROM events WHERE status = 'active' ORDER BY name ASC")

    @classmethod
    def create(cls, name: str, description: str, location: str, event_date: str, start_time: str, end_time: str, status: str = "active") -> int:
        return db.execute_write(
            """
            INSERT INTO events (name, description, location, event_date, start_time, end_time, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name.strip(), description.strip(), location.strip(), event_date, start_time, end_time, status)
        )

    @classmethod
    def update(cls, event_id: int, name: str, description: str, location: str, event_date: str, start_time: str, end_time: str, status: str) -> None:
        db.execute_write(
            """
            UPDATE events
            SET name = %s, description = %s, location = %s, event_date = %s, start_time = %s, end_time = %s, status = %s
            WHERE id = %s
            """,
            (name.strip(), description.strip(), location.strip(), event_date, start_time, end_time, status, event_id)
        )

    @classmethod
    def delete(cls, event_id: int) -> None:
        db.execute_write("DELETE FROM events WHERE id = %s", (event_id,))
