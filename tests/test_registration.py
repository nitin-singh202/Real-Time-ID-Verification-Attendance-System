import pytest
from models.participant import Participant
from database.db import db


@pytest.fixture(autouse=True)
def setup_db():
    db.init_db()


def test_valid_participant_registration():
    reg_no = "TEST_REG_101"
    # Clean prior if any
    db.execute_write("DELETE FROM participants WHERE registration_number = %s", (reg_no,))

    participant = Participant.create(
        name="Nitin Kumar",
        registration_number=reg_no,
        event_name="Tech Fest 2026",
        email="nitin@test.com",
        phone="9876543210",
        category="Student"
    )

    assert participant is not None
    assert participant["name"] == "Nitin Kumar"
    assert participant["registration_number"] == reg_no
    assert participant["participant_uuid"] is not None
    assert participant["qr_code_path"] is not None


def test_duplicate_registration_rejected():
    reg_no = "TEST_REG_DUP"
    db.execute_write("DELETE FROM participants WHERE registration_number = %s", (reg_no,))

    Participant.create(
        name="Original User",
        registration_number=reg_no,
        event_name="Tech Fest 2026"
    )

    # Attempt duplicate
    with pytest.raises(ValueError) as excinfo:
        Participant.create(
            name="Duplicate User",
            registration_number=reg_no,
            event_name="Tech Fest 2026"
        )
    assert "already exists" in str(excinfo.value)
