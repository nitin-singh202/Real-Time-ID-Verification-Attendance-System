import json
import logging
from typing import Dict, Any, Tuple, Optional
from database.db import db

logger = logging.getLogger("attendance_system.verification")


class VerificationService:
    """Service to parse, validate, and verify QR payloads against the database."""

    @staticmethod
    def parse_payload(raw_data: str) -> Tuple[bool, Dict[str, Any], str]:
        """
        Parse raw QR string.
        Supports structured JSON as well as raw registration number fallback.
        """
        if not raw_data or not raw_data.strip():
            return False, {}, "Empty QR payload"

        raw_data = raw_data.strip()

        # Try parsing JSON payload
        try:
            payload = json.loads(raw_data)
            if isinstance(payload, dict):
                participant_uuid = payload.get("participant_id") or payload.get("id") or payload.get("uuid")
                reg_no = payload.get("registration_number") or payload.get("reg_no")
                
                if not reg_no and not participant_uuid:
                    return False, {}, "Invalid QR structure: missing registration identifier"
                    
                return True, {
                    "participant_uuid": participant_uuid,
                    "registration_number": reg_no
                }, "Success"
        except (json.JSONDecodeError, ValueError):
            pass

        # Fallback: Plain registration number / UUID string
        # Clean from any stray characters
        clean_code = raw_data.strip()
        return True, {
            "participant_uuid": None,
            "registration_number": clean_code
        }, "Legacy / Plain format"

    @classmethod
    def verify_participant(cls, raw_qr_data: str) -> Tuple[str, Optional[Dict[str, Any]], str]:
        """
        Verify QR data against database.
        Returns:
            status: 'VERIFIED' | 'NOT_FOUND' | 'INVALID_QR'
            participant_data: dict or None
            message: descriptive feedback string
        """
        success, parsed_data, parse_msg = cls.parse_payload(raw_qr_data)
        if not success:
            logger.warning(f"QR parse failed: {parse_msg}")
            return "INVALID_QR", None, "Invalid or unreadable QR code format."

        participant_uuid = parsed_data.get("participant_uuid")
        registration_number = parsed_data.get("registration_number")

        participant = None

        # 1. Search by exact UUID if present
        if participant_uuid:
            participant = db.query_one(
                "SELECT * FROM participants WHERE participant_uuid = %s",
                (participant_uuid,)
            )

        # 2. Search by registration number if not found by UUID
        if not participant and registration_number:
            participant = db.query_one(
                "SELECT * FROM participants WHERE registration_number = %s",
                (registration_number,)
            )

        if not participant:
            logger.warning(f"Participant lookup failed for: {parsed_data}")
            return "NOT_FOUND", None, f"Participant with ID/Reg No '{registration_number or participant_uuid}' is not registered."

        return "VERIFIED", participant, f"Participant verified: {participant.get('name')}"
