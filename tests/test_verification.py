import json
import pytest
from services.verification_service import VerificationService
from models.participant import Participant
from database.db import db


@pytest.fixture(autouse=True)
def setup_db():
    db.init_db()


def test_registered_participant_verification():
    reg_no = "VERIFY_TEST_101"
    db.execute_write("DELETE FROM participants WHERE registration_number = %s", (reg_no,))

    participant = Participant.create(
        name="Verification User",
        registration_number=reg_no,
        event_name="Tech Fest 2026"
    )

    # Valid JSON payload
    payload = json.dumps({
        "participant_id": participant["participant_uuid"],
        "registration_number": reg_no
    })

    status, found, msg = VerificationService.verify_participant(payload)
    assert status == "VERIFIED"
    assert found is not None
    assert found["registration_number"] == reg_no


def test_unregistered_participant_verification():
    payload = json.dumps({
        "participant_id": "non-existent-uuid",
        "registration_number": "UNREGISTERED_999"
    })

    status, found, msg = VerificationService.verify_participant(payload)
    assert status == "NOT_FOUND"
    assert found is None
