import csv
import io
from flask import Blueprint, render_template, request, send_file, Response, flash, redirect, url_for
from models.attendance import Attendance
from models.event import Event
from services.excel_service import ExcelService
from config import Config

reports_bp = Blueprint("reports", __name__)


@reports_bp.route("/reports")
def index():
    events = Event.get_all()
    selected_event = request.args.get("event", "")
    date_filter = request.args.get("date", "")
    status_filter = request.args.get("status", "")

    records = Attendance.get_all(
        event_name=selected_event,
        date_filter=date_filter,
        status_filter=status_filter
    )

    return render_template(
        "reports.html",
        events=events,
        records=records,
        selected_event=selected_event,
        selected_date=date_filter,
        selected_status=status_filter
    )


@reports_bp.route("/reports/export/excel")
def export_excel():
    event_filter = request.args.get("event", "")
    date_filter = request.args.get("date", "")
    status_filter = request.args.get("status", "")

    records = Attendance.get_all(
        event_name=event_filter,
        date_filter=date_filter,
        status_filter=status_filter
    )

    if not records:
        flash("No attendance records to export for the chosen filter.", "warning")
        return redirect(url_for("reports.index"))

    event_label = event_filter if event_filter and event_filter != "all" else "All_Events"
    file_path = ExcelService.generate_attendance_report(records, event_label)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=f"Attendance_{event_label}.xlsx"
    )


@reports_bp.route("/reports/export/csv")
def export_csv():
    event_filter = request.args.get("event", "")
    date_filter = request.args.get("date", "")
    status_filter = request.args.get("status", "")

    records = Attendance.get_all(
        event_name=event_filter,
        date_filter=date_filter,
        status_filter=status_filter
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Participant Name", "Registration Number", "Event",
        "Status", "Entry Time", "Exit Time", "Verification Method"
    ])

    for r in records:
        writer.writerow([
            r.get("id"),
            r.get("name"),
            r.get("registration_number"),
            r.get("event_name"),
            r.get("status"),
            r.get("entry_time"),
            r.get("exit_time") or "",
            r.get("verification_method")
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance_export.csv"}
    )


@reports_bp.route("/reports/download/master")
def download_master():
    master_file = Config.EXCEL_MASTER_FILE
    if not master_file.exists():
        flash("Master Excel file not created yet. Register participants to initialize.", "warning")
        return redirect(url_for("reports.index"))

    return send_file(
        str(master_file),
        as_attachment=True,
        download_name="Master_Attendance_Record.xlsx"
    )
