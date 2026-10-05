import pytest
from models.participant import Participant
from services.attendance_service import AttendanceService
from database.db import db


@pytest.fixture(autouse=True)
def setup_db():
    db.init_db()


def test_first_scan_and_duplicate_scan_prevention():
    reg_no = "ATTEND_TEST_202"
    db.execute_write("DELETE FROM participants WHERE registration_number = %s", (reg_no,))

    participant = Participant.create(
        name="Attendance Attendee",
        registration_number=reg_no,
        event_name="Tech Fest 2026"
    )

    # Clean cooldown cache for test isolation
    AttendanceService._scan_cooldowns.pop(reg_no, None)

    # 1. First Scan -> New Entry
    res1 = AttendanceService.process_scan(
        participant=participant,
        event_name="Tech Fest 2026",
        verification_method="TEST_SCAN"
    )
    assert res1["success"] is True
    assert res1["status"] == "VERIFIED_NEW"
    assert res1["entry_time"] is not None

    # 2. Immediate Repeat Frame Scan -> Cooldown Acknowledged
    res2 = AttendanceService.process_scan(
        participant=participant,
        event_name="Tech Fest 2026",
        verification_method="TEST_SCAN"
    )
    assert res2["status"] == "COOLDOWN_IGNORED"

    # 3. Simulate after cooldown expired
    AttendanceService._scan_cooldowns.pop(reg_no, None)
    res3 = AttendanceService.process_scan(
        participant=participant,
        event_name="Tech Fest 2026",
        verification_method="TEST_SCAN"
    )
    assert res3["status"] == "ALREADY_VERIFIED"
    assert "Already marked present" in res3["message"]
