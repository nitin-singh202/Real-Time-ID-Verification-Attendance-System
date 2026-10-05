import time
import threading
import logging
from typing import Optional, Dict, Any, Generator
import cv2
import numpy as np
from config import Config
from services.verification_service import VerificationService
from services.attendance_service import AttendanceService

logger = logging.getLogger("attendance_system.qr_scanner")


class CameraScanner:
    """
    OpenCV Camera and QR Code Scanner Engine.
    Handles video streaming, real-time QR detection, bounding box overlays,
    and automatic database verification & attendance recording.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(CameraScanner, cls).__new__(cls)
                cls._instance._init_engine()
            return cls._instance

    def _init_engine(self):
        self.camera_index = Config.CAMERA_INDEX
        self.is_running = False
        self.cap: Optional[cv2.VideoCapture] = None
        self.detector = cv2.QRCodeDetector()
        self.current_frame = None
        self.target_event = None
        self.is_exit_mode = False
        self.camera_error: Optional[str] = None
        self.last_scan_result: Dict[str, Any] = {
            "status": "IDLE",
            "message": "Scanner ready. Present QR code to camera.",
            "badge_status": "neutral",
            "timestamp": time.time(),
            "participant": None
        }
        self.capture_thread: Optional[threading.Thread] = None

    def start_camera(self, camera_index: Optional[int] = None):
        """Start background camera capture loop."""
        if camera_index is not None:
            self.camera_index = camera_index

        if self.is_running and self.cap and self.cap.isOpened():
            return

        self.is_running = True
        self.camera_error = None
        self.capture_thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.capture_thread.start()
        logger.info(f"Camera scanner started on device index {self.camera_index}")

    def stop_camera(self):
        """Stop camera capture loop and release device."""
        self.is_running = False
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        logger.info("Camera scanner stopped.")

    def set_event(self, event_name: Optional[str]):
        """Set active event for attendance recording."""
        self.target_event = event_name

    def set_exit_mode(self, is_exit: bool):
        """Set whether scanner is recording Exit or Entry."""
        self.is_exit_mode = is_exit

    def get_latest_scan_result(self) -> Dict[str, Any]:
        """Return the most recent scan result for UI polling."""
        return self.last_scan_result

    def _create_placeholder_frame(self, message: str) -> np.ndarray:
        """Create a dark, stylized placeholder frame when camera is unavailable."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (15, 23, 42)  # Slate-900 background

        # Draw grid accent lines
        cv2.line(frame, (40, 40), (600, 40), (30, 41, 59), 2)
        cv2.line(frame, (40, 440), (600, 440), (30, 41, 59), 2)

        # Draw Camera Icon / Status
        cv2.putText(frame, "LIVE SCANNER FEED", (50, 80), cv2.FONT_HERSHEY_DUPLEX, 0.7, (59, 130, 246), 2)
        cv2.putText(frame, message, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (226, 232, 240), 1)
        cv2.putText(frame, "Checking camera device index: " + str(self.camera_index), (50, 280), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (148, 163, 184), 1)
        return frame

    def _capture_worker(self):
        """Background thread reading frames and decoding QR codes."""
        try:
            # On Windows, cv2.CAP_DSHOW or default CAP_ANY is standard
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_ANY)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)

            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, Config.CAMERA_WIDTH)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, Config.CAMERA_HEIGHT)
                self.cap.set(cv2.CAP_PROP_FPS, Config.CAMERA_FPS)
            else:
                self.camera_error = f"Camera index {self.camera_index} could not be opened. Check connection or privacy permissions."
                logger.warning(self.camera_error)
        except Exception as e:
            self.camera_error = f"Camera initialization error: {e}"
            logger.error(self.camera_error)

        while self.is_running:
            if not self.cap or not self.cap.isOpened() or self.camera_error:
                self.current_frame = self._create_placeholder_frame(
                    self.camera_error or "Camera offline / reconnecting..."
                )
                time.sleep(0.5)
                # Attempt periodic reconnect
                if not self.camera_error:
                    try:
                        self.cap = cv2.VideoCapture(self.camera_index)
                        if self.cap.isOpened():
                            self.camera_error = None
                    except Exception:
                        pass
                continue

            ret, frame = self.cap.read()
            if not ret or frame is None:
                self.current_frame = self._create_placeholder_frame("No video frame received from camera.")
                time.sleep(0.1)
                continue

            # Process frame for QR codes
            processed_frame = self._process_frame(frame)
            self.current_frame = processed_frame

            time.sleep(0.01)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Detect QR code, draw bounding box & visual HUD, and trigger attendance verification."""
        display_frame = frame.copy()
        h, w, _ = display_frame.shape

        # Scanner visual target guide (Corner brackets)
        center_x, center_y = w // 2, h // 2
        box_size = min(w, h) // 3
        x1, y1 = center_x - box_size, center_y - box_size
        x2, y2 = center_x + box_size, center_y + box_size

        # Subtle target reticle in center
        cv2.rectangle(display_frame, (x1, y1), (x2, y2), (255, 255, 255), 1)

        # Detect and decode QR Code
        try:
            decoded_text, points, _ = self.detector.detectAndDecode(frame)
            
            # If multi-detector or bounding points found
            if points is not None and len(points) > 0:
                pts = points.astype(int).reshape(-1, 2)
                
                # Draw polygon around QR code
                cv2.polylines(display_frame, [pts], isClosed=True, color=(59, 130, 246), thickness=3)

                if decoded_text and decoded_text.strip():
                    self._handle_qr_detection(decoded_text.strip(), pts, display_frame)

        except Exception as ex:
            logger.debug(f"QR detection frame error: {ex}")

        # Draw HUD status banner on bottom of frame
        self._draw_hud(display_frame)

        return display_frame

    def _handle_qr_detection(self, decoded_text: str, pts: np.ndarray, frame: np.ndarray):
        """Process verified decoded QR payload."""
        status_code, participant, message = VerificationService.verify_participant(decoded_text)

        if status_code == "VERIFIED" and participant:
            # Process attendance and duplicate prevention
            res = AttendanceService.process_scan(
                participant=participant,
                event_name=self.target_event,
                verification_method="QR_SCAN",
                is_exit_scan=self.is_exit_mode
            )

            # Determine bounding box color
            if res["status"] == "VERIFIED_NEW":
                box_color = (34, 197, 94)  # Vibrant Green
                cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=4)
                cv2.putText(frame, "✓ VERIFIED", (pts[0][0], max(30, pts[0][1] - 10)),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, box_color, 2)
            elif res["status"] == "ALREADY_VERIFIED" or res["status"] == "COOLDOWN_IGNORED":
                box_color = (234, 179, 8)  # Amber / Yellow
                cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=4)
                cv2.putText(frame, "ALREADY SCANNED", (pts[0][0], max(30, pts[0][1] - 10)),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, box_color, 2)
            elif res["status"] == "EXIT_RECORDED":
                box_color = (59, 130, 246)  # Blue
                cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=4)
                cv2.putText(frame, "✓ EXIT RECORDED", (pts[0][0], max(30, pts[0][1] - 10)),
                            cv2.FONT_HERSHEY_DUPLEX, 0.8, box_color, 2)

            # Update cache if it's not a silent cooldown
            if res["status"] != "COOLDOWN_IGNORED":
                self.last_scan_result = {
                    "status": res["status"],
                    "badge_status": res["badge_status"],
                    "message": res["message"],
                    "timestamp": time.time(),
                    "participant": participant,
                    "entry_time": res.get("entry_time"),
                    "exit_time": res.get("exit_time"),
                    "event_name": res.get("event_name", participant.get("event_name"))
                }

        else:
            # Invalid or Unregistered QR
            box_color = (239, 68, 68)  # Bright Red
            cv2.polylines(frame, [pts], isClosed=True, color=box_color, thickness=4)
            cv2.putText(frame, "✗ NOT VERIFIED", (pts[0][0], max(30, pts[0][1] - 10)),
                        cv2.FONT_HERSHEY_DUPLEX, 0.8, box_color, 2)

            self.last_scan_result = {
                "status": "NOT_FOUND",
                "badge_status": "danger",
                "message": message,
                "timestamp": time.time(),
                "participant": None,
                "raw_text": decoded_text[:30]
            }

    def _draw_hud(self, frame: np.ndarray):
        """Draw on-screen HUD (status bar, event mode, time)."""
        h, w, _ = frame.shape
        # Top banner overlay
        cv2.rectangle(frame, (0, 0), (w, 40), (15, 23, 42), -1)
        mode_str = "EXIT SCANNING" if self.is_exit_mode else "ENTRY SCANNING"
        event_str = f"Event: {self.target_event or 'Active Event'}"
        time_str = time.strftime("%H:%M:%S")

        cv2.putText(frame, f"● LIVE GATE | {mode_str}", (15, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (34, 197, 94), 2)
        cv2.putText(frame, f"{event_str} | {time_str}", (w - 320, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (226, 232, 240), 1)

    def generate_mjpeg_stream(self) -> Generator[bytes, None, None]:
        """Yield multipart MJPEG stream for HTTP video response."""
        self.start_camera()

        while True:
            if self.current_frame is None:
                frame = self._create_placeholder_frame("Initializing video stream...")
            else:
                frame = self.current_frame

            # Encode as JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                time.sleep(0.05)
                continue

            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            time.sleep(0.033)  # ~30 FPS

    def scan_image_file(self, image_path: str, event_name: Optional[str] = None) -> Dict[str, Any]:
        """Decode and process a QR code from a static image file."""
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "status": "FILE_ERROR", "message": "Could not read image file."}

        decoded_text, points, _ = self.detector.detectAndDecode(img)
        if not decoded_text or not decoded_text.strip():
            return {"success": False, "status": "NO_QR", "message": "No valid QR code detected in the image."}

        status_code, participant, message = VerificationService.verify_participant(decoded_text.strip())
        if status_code != "VERIFIED" or not participant:
            return {
                "success": False,
                "status": status_code,
                "badge_status": "danger",
                "message": message,
                "participant": None
            }

        res = AttendanceService.process_scan(
            participant=participant,
            event_name=event_name or self.target_event,
            verification_method="IMAGE_UPLOAD"
        )
        return res


# Global Camera Scanner Instance
scanner = CameraScanner()
