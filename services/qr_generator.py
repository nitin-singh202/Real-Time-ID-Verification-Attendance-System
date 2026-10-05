import json
import logging
from pathlib import Path
import qrcode
from PIL import Image, ImageDraw, ImageFont
from config import Config

logger = logging.getLogger("attendance_system.qr_generator")


class QRGenerator:
    """Service to generate secure, standardized QR codes for registered participants."""

    @staticmethod
    def generate(participant_uuid: str, registration_number: str, participant_name: str = "", event_name: str = "") -> str:
        """
        Generate and save a high-contrast, robust QR code image.
        Returns the relative file path of the saved QR code.
        """
        Config.QR_CODES_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"{participant_uuid}.png"
        filepath = Config.QR_CODES_DIR / filename

        payload = {
            "participant_id": participant_uuid,
            "registration_number": registration_number,
            "system": "ID_ATTENDANCE_SYSTEM_V1"
        }
        payload_str = json.dumps(payload, separators=(',', ':'))

        # Create QR Code instance with high error correction (ErrorCorrection.H allows decorative center badge if needed)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(payload_str)
        qr.make(fit=True)

        img = qr.make_image(fill_color="#0F172A", back_color="#FFFFFF").convert('RGBA')

        # Add participant label footer below QR code for printable cards
        card_width = img.width
        card_height = img.height + 40
        card = Image.new("RGBA", (card_width, card_height), "#FFFFFF")
        card.paste(img, (0, 0))

        draw = ImageDraw.Draw(card)
        label_text = f"{registration_number}"
        # Center the label text at bottom
        try:
            # Simple text rendering
            bbox = draw.textbbox((0, 0), label_text)
            text_w = bbox[2] - bbox[0]
            text_h = bbox[3] - bbox[1]
            pos_x = (card_width - text_w) // 2
            pos_y = img.height + (40 - text_h) // 2 - 2
            draw.text((pos_x, pos_y), label_text, fill="#334155")
        except Exception:
            # Fallback if textbbox fails in older pillow
            draw.text((card_width // 4, img.height + 8), label_text, fill="#334155")

        card.save(filepath, format="PNG")
        logger.info(f"QR Code generated and saved to {filepath}")
        return f"qr_codes/{filename}"

    @staticmethod
    def get_absolute_path(relative_path: str) -> Path:
        """Get absolute path from relative stored path."""
        clean_path = relative_path.replace("qr_codes/", "")
        return Config.QR_CODES_DIR / clean_path
