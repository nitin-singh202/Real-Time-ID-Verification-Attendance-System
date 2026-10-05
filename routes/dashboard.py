from flask import Blueprint, render_template, request
from services.attendance_service import AttendanceService
from models.event import Event

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    selected_event = request.args.get("event", "")
    metrics = AttendanceService.get_dashboard_metrics(selected_event)
    events = Event.get_all()
    return render_template(
        "dashboard.html",
        metrics=metrics,
        events=events,
        selected_event=selected_event
    )
