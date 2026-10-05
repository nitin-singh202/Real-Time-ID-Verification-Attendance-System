import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.db import db
from models.event import Event
from models.participant import Participant


def seed_data():
    print("Initializing database...")
    db.init_db()

    events_data = [
        {
            "name": "Tech Fest 2026",
            "description": "Annual Technology and Innovation Festival",
            "location": "Campus Auditorium",
            "event_date": "2026-10-10",
            "start_time": "09:00:00",
            "end_time": "18:00:00",
            "status": "active"
        },
        {
            "name": "AI Workshop 2026",
            "description": "Hands-on Deep Learning & Computer Vision Workshop",
            "location": "Seminar Hall B",
            "event_date": "2026-10-15",
            "start_time": "10:00:00",
            "end_time": "16:00:00",
            "status": "active"
        },
        {
            "name": "CSE 301 - Operating Systems",
            "description": "Fall 2026 Regular Lecture Series",
            "location": "Lecture Hall 104",
            "event_date": "2026-10-05",
            "start_time": "08:30:00",
            "end_time": "10:00:00",
            "status": "active"
        }
    ]

    for ev in events_data:
        existing = Event.get_by_name(ev["name"])
        if not existing:
            Event.create(**ev)
            print(f"Created Event: {ev['name']}")

    participants_data = [
        {
            "name": "Rahul Sharma",
            "registration_number": "23BCE1234",
            "email": "rahul.sharma@example.com",
            "phone": "+91 9876543210",
            "event_name": "Tech Fest 2026",
            "category": "Student"
        },
        {
            "name": "Ankit Singh",
            "registration_number": "23BCE1122",
            "email": "ankit.singh@example.com",
            "phone": "+91 9876543211",
            "event_name": "Tech Fest 2026",
            "category": "Student"
        },
        {
            "name": "Priya Sharma",
            "registration_number": "23BCE1421",
            "email": "priya.sharma@example.com",
            "phone": "+91 9876543212",
            "event_name": "AI Workshop 2026",
            "category": "Delegate"
        },
        {
            "name": "Dr. Arvind Mehta",
            "registration_number": "FAC8801",
            "email": "arvind.mehta@example.com",
            "phone": "+91 9876543213",
            "event_name": "AI Workshop 2026",
            "category": "Speaker"
        }
    ]

    for p in participants_data:
        existing = Participant.get_by_reg_no(p["registration_number"])
        if not existing:
            created = Participant.create(**p)
            print(f"Enrolled Participant: {p['name']} ({p['registration_number']}) -> QR saved to {created['qr_code_path']}")

    print("\nDatabase seeded successfully!")


if __name__ == "__main__":
    seed_data()
