import os
from pathlib import Path
from flask import Blueprint, render_template, Response, request, jsonify
from services.qr_scanner import scanner
from services.verification_service import VerificationService
from services.attendance_service import AttendanceService
from models.event import Event
from config import Config

scanner_bp = Blueprint("scanner", __name__)


@scanner_bp.route("/scanner")
def live_scanner():
    events = Event.get_all()
    selected_event = request.args.get("event", "")
    if selected_event:
        scanner.set_event(selected_event)
    return render_template(
        "scanner.html",
        events=events,
        selected_event=selected_event or scanner.target_event,
        camera_index=scanner.camera_index
    )


@scanner_bp.route("/video_feed")
def video_feed():
    """MJPEG streaming route for web client."""
    return Response(
        scanner.generate_mjpeg_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@scanner_bp.route("/api/scan_status")
def scan_status():
    """Live scan result polled by frontend."""
    return jsonify(scanner.get_latest_scan_result())


@scanner_bp.route("/api/scanner/settings", methods=["POST"])
def update_settings():
    """Update active event, entry/exit mode, or camera index."""
    data = request.get_json() or {}
    if "event_name" in data:
        scanner.set_event(data["event_name"])
    if "is_exit_mode" in data:
        scanner.set_exit_mode(bool(data["is_exit_mode"]))
    if "camera_index" in data:
        try:
            new_index = int(data["camera_index"])
            scanner.stop_camera()
            scanner.start_camera(new_index)
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 400

    return jsonify({
        "success": True,
        "target_event": scanner.target_event,
        "is_exit_mode": scanner.is_exit_mode,
        "camera_index": scanner.camera_index
    })


@scanner_bp.route("/api/scan_manual", methods=["POST"])
def scan_manual():
    """Manual registration number or QR string verification."""
    data = request.get_json() or {}
    code = data.get("code", "").strip()
    event_name = data.get("event_name", scanner.target_event)
    is_exit = bool(data.get("is_exit", scanner.is_exit_mode))

    if not code:
        return jsonify({"success": False, "message": "Code or registration number is required."}), 400

    status_code, participant, message = VerificationService.verify_participant(code)
    if status_code != "VERIFIED" or not participant:
        return jsonify({
            "success": False,
            "status": "NOT_FOUND",
            "badge_status": "danger",
            "message": message,
            "participant": None
        })

    res = AttendanceService.process_scan(
        participant=participant,
        event_name=event_name,
        verification_method="MANUAL_INPUT",
        is_exit_scan=is_exit
    )
    return jsonify(res)


@scanner_bp.route("/api/scan_upload", methods=["POST"])
def scan_upload():
    """Upload an image file to decode and mark attendance."""
    if "qr_image" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded."}), 400

    file = request.files["qr_image"]
    if not file.filename:
        return jsonify({"success": False, "message": "Empty filename."}), 400

    temp_path = Config.DATA_DIR / f"temp_upload_{file.filename}"
    file.save(str(temp_path))

    event_name = request.form.get("event_name", scanner.target_event)
    try:
        result = scanner.scan_image_file(str(temp_path), event_name=event_name)
    finally:
        if temp_path.exists():
            try:
                os.remove(temp_path)
            except Exception:
                pass

    return jsonify(result)
