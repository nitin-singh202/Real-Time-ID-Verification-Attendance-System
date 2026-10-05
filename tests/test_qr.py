import cv2
import json
from services.qr_generator import QRGenerator
from config import Config


def test_qr_generation_and_opencv_decoding():
    uuid_val = "test-uuid-999"
    reg_no = "TEST_QR_999"

    qr_rel_path = QRGenerator.generate(
        participant_uuid=uuid_val,
        registration_number=reg_no,
        participant_name="Test Student",
        event_name="Tech Fest 2026"
    )

    abs_path = QRGenerator.get_absolute_path(qr_rel_path)
    assert abs_path.exists()

    # Decode with OpenCV QRCodeDetector
    img = cv2.imread(str(abs_path))
    assert img is not None

    detector = cv2.QRCodeDetector()
    decoded_text, points, _ = detector.detectAndDecode(img)

    assert decoded_text != ""
    data = json.loads(decoded_text)
    assert data["participant_id"] == uuid_val
    assert data["registration_number"] == reg_no
