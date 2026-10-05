import uuid
from typing import Optional, List, Dict, Any
from database.db import db
from services.qr_generator import QRGenerator
from services.excel_service import ExcelService
from config import Config


class Participant:
    """Participant model for attendees, students, delegates, etc."""

    @classmethod
    def get_all(cls, search: str = "", event_filter: str = "") -> List[Dict[str, Any]]:
        """Retrieve participants with optional search and event filtering."""
        sql = "SELECT * FROM participants WHERE 1=1"
        params = []

        if event_filter and event_filter != "all":
            sql += " AND event_name = %s"
            params.append(event_filter)

        if search and search.strip():
            term = f"%{search.strip()}%"
            sql += " AND (name LIKE %s OR registration_number LIKE %s OR email LIKE %s)"
            params.extend([term, term, term])

        sql += " ORDER BY id DESC"
        return db.query_all(sql, tuple(params))

    @classmethod
    def get_by_id(cls, participant_id: int) -> Optional[Dict[str, Any]]:
        return db.query_one("SELECT * FROM participants WHERE id = %s", (participant_id,))

    @classmethod
    def get_by_uuid(cls, participant_uuid: str) -> Optional[Dict[str, Any]]:
        return db.query_one("SELECT * FROM participants WHERE participant_uuid = %s", (participant_uuid,))

    @classmethod
    def get_by_reg_no(cls, reg_no: str) -> Optional[Dict[str, Any]]:
        return db.query_one("SELECT * FROM participants WHERE registration_number = %s", (reg_no.strip(),))

    @classmethod
    def create(
        cls,
        name: str,
        registration_number: str,
        event_name: str,
        email: str = "",
        phone: str = "",
        category: str = "Participant"
    ) -> Dict[str, Any]:
        """
        Validate, create a participant, generate unique QR code, and sync to Excel.
        """
        reg_no = registration_number.strip().upper()
        clean_name = name.strip()

        # Validation: check uniqueness
        existing = cls.get_by_reg_no(reg_no)
        if existing:
            raise ValueError(f"Registration Number '{reg_no}' already exists in database.")

        participant_uuid = str(uuid.uuid4())

        # Generate QR code
        qr_path = QRGenerator.generate(
            participant_uuid=participant_uuid,
            registration_number=reg_no,
            participant_name=clean_name,
            event_name=event_name
        )

        participant_id = db.execute_write(
            """
            INSERT INTO participants (participant_uuid, name, registration_number, email, phone, event_name, category, qr_code_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (participant_uuid, clean_name, reg_no, email.strip(), phone.strip(), event_name.strip(), category.strip(), qr_path)
        )

        created_record = cls.get_by_id(participant_id)

        # Sync to Master Excel record
        if Config.EXCEL_AUTO_SYNC:
            ExcelService.sync_to_master(created_record)

        return created_record

    @classmethod
    def update(
        cls,
        participant_id: int,
        name: str,
        registration_number: str,
        event_name: str,
        email: str = "",
        phone: str = "",
        category: str = "Participant"
    ) -> Dict[str, Any]:
        """Update participant info and regenerate QR code if registration number changed."""
        existing = cls.get_by_id(participant_id)
        if not existing:
            raise ValueError("Participant not found.")

        reg_no = registration_number.strip().upper()
        # Check uniqueness if changed
        if reg_no != existing["registration_number"]:
            duplicate = cls.get_by_reg_no(reg_no)
            if duplicate and duplicate["id"] != participant_id:
                raise ValueError(f"Registration number '{reg_no}' is already taken.")

        # Regenerate QR Code
        qr_path = QRGenerator.generate(
            participant_uuid=existing["participant_uuid"],
            registration_number=reg_no,
            participant_name=name.strip(),
            event_name=event_name.strip()
        )

        db.execute_write(
            """
            UPDATE participants
            SET name = %s, registration_number = %s, email = %s, phone = %s, event_name = %s, category = %s, qr_code_path = %s
            WHERE id = %s
            """,
            (name.strip(), reg_no, email.strip(), phone.strip(), event_name.strip(), category.strip(), qr_path, participant_id)
        )

        updated_record = cls.get_by_id(participant_id)
        if Config.EXCEL_AUTO_SYNC:
            ExcelService.sync_to_master(updated_record)

        return updated_record

    @classmethod
    def delete(cls, participant_id: int) -> None:
        db.execute_write("DELETE FROM participants WHERE id = %s", (participant_id,))
