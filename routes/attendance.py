from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from models.attendance import Attendance
from models.event import Event
from models.participant import Participant
from services.attendance_service import AttendanceService

attendance_bp = Blueprint("attendance", __name__)


@attendance_bp.route("/attendance")
def list_attendance():
    event_filter = request.args.get("event", "")
    date_filter = request.args.get("date", "")
    status_filter = request.args.get("status", "")
    search = request.args.get("search", "")

    records = Attendance.get_all(
        event_name=event_filter,
        date_filter=date_filter,
        status_filter=status_filter,
        search=search
    )
    events = Event.get_all()

    return render_template(
        "attendance.html",
        records=records,
        events=events,
        selected_event=event_filter,
        selected_date=date_filter,
        selected_status=status_filter,
        search=search
    )


@attendance_bp.route("/api/attendance/mark_manual", methods=["POST"])
def mark_manual():
    data = request.get_json() or {}
    reg_no = data.get("registration_number", "").strip()
    event_name = data.get("event_name", "").strip()

    if not reg_no or not event_name:
        return jsonify({"success": False, "message": "Registration number and event are required."}), 400

    participant = Participant.get_by_reg_no(reg_no)
    if not participant:
        return jsonify({"success": False, "message": f"Participant '{reg_no}' not found."}), 404

    res = AttendanceService.process_scan(
        participant=participant,
        event_name=event_name,
        verification_method="MANUAL_ADMIN"
    )
    return jsonify(res)


@attendance_bp.route("/attendance/<int:attendance_id>/delete", methods=["POST"])
def delete_attendance(attendance_id):
    try:
        Attendance.delete(attendance_id)
        flash("Attendance record deleted.", "success")
    except Exception as e:
        flash(f"Error deleting record: {str(e)}", "danger")

    return redirect(url_for("attendance.list_attendance"))
