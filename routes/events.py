from flask import Blueprint, render_template, request, redirect, url_for, flash
from models.event import Event

events_bp = Blueprint("events", __name__)


@events_bp.route("/events")
def list_events():
    events = Event.get_all()
    return render_template("events.html", events=events)


@events_bp.route("/events/create", methods=["POST"])
def create_event():
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip() or "Main Auditorium"
    event_date = request.form.get("event_date", "").strip()
    start_time = request.form.get("start_time", "").strip() or "09:00:00"
    end_time = request.form.get("end_time", "").strip() or "17:00:00"
    status = request.form.get("status", "active")

    if not name or not event_date:
        flash("Event Name and Date are required.", "danger")
        return redirect(url_for("events.list_events"))

    try:
        Event.create(
            name=name,
            description=description,
            location=location,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            status=status
        )
        flash(f"Event '{name}' created successfully.", "success")
    except Exception as e:
        flash(f"Error creating event: {str(e)}", "danger")

    return redirect(url_for("events.list_events"))


@events_bp.route("/events/<int:event_id>/edit", methods=["POST"])
def edit_event(event_id):
    name = request.form.get("name", "").strip()
    description = request.form.get("description", "").strip()
    location = request.form.get("location", "").strip()
    event_date = request.form.get("event_date", "").strip()
    start_time = request.form.get("start_time", "").strip()
    end_time = request.form.get("end_time", "").strip()
    status = request.form.get("status", "active")

    try:
        Event.update(
            event_id=event_id,
            name=name,
            description=description,
            location=location,
            event_date=event_date,
            start_time=start_time,
            end_time=end_time,
            status=status
        )
        flash(f"Event '{name}' updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating event: {str(e)}", "danger")

    return redirect(url_for("events.list_events"))


@events_bp.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    try:
        Event.delete(event_id)
        flash("Event deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting event: {str(e)}", "danger")

    return redirect(url_for("events.list_events"))
