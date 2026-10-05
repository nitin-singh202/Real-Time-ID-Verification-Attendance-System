from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file
from models.participant import Participant
from models.event import Event
from services.qr_generator import QRGenerator

participants_bp = Blueprint("participants", __name__)


@participants_bp.route("/register", methods=["GET", "POST"])
def register():
    events = Event.get_all()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        reg_no = request.form.get("registration_number", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        event_name = request.form.get("event_name", "").strip()
        category = request.form.get("category", "Participant").strip()

        # Validation
        if not name:
            flash("Full Name is required.", "danger")
            return render_template("register.html", events=events, form=request.form)

        if not reg_no:
            flash("Registration Number is required.", "danger")
            return render_template("register.html", events=events, form=request.form)

        if not event_name:
            flash("Please select or specify an event.", "danger")
            return render_template("register.html", events=events, form=request.form)

        try:
            participant = Participant.create(
                name=name,
                registration_number=reg_no,
                event_name=event_name,
                email=email,
                phone=phone,
                category=category
            )
            flash(f"Participant '{name}' ({reg_no}) registered successfully!", "success")
            return render_template("register.html", events=events, new_participant=participant)
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("register.html", events=events, form=request.form)
        except Exception as e:
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return render_template("register.html", events=events, form=request.form)

    return render_template("register.html", events=events)


@participants_bp.route("/participants")
def list_participants():
    search = request.args.get("search", "")
    event_filter = request.args.get("event", "")
    participants = Participant.get_all(search=search, event_filter=event_filter)
    events = Event.get_all()
    return render_template(
        "participants.html",
        participants=participants,
        events=events,
        search=search,
        selected_event=event_filter
    )


@participants_bp.route("/participants/<int:participant_id>/edit", methods=["POST"])
def edit_participant(participant_id):
    name = request.form.get("name", "").strip()
    reg_no = request.form.get("registration_number", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()
    event_name = request.form.get("event_name", "").strip()
    category = request.form.get("category", "Participant").strip()

    try:
        Participant.update(
            participant_id=participant_id,
            name=name,
            registration_number=reg_no,
            event_name=event_name,
            email=email,
            phone=phone,
            category=category
        )
        flash(f"Participant '{name}' updated successfully.", "success")
    except Exception as e:
        flash(f"Error updating participant: {str(e)}", "danger")

    return redirect(url_for("participants.list_participants"))


@participants_bp.route("/participants/<int:participant_id>/delete", methods=["POST"])
def delete_participant(participant_id):
    try:
        Participant.delete(participant_id)
        flash("Participant deleted successfully.", "success")
    except Exception as e:
        flash(f"Error deleting participant: {str(e)}", "danger")

    return redirect(url_for("participants.list_participants"))


@participants_bp.route("/participants/<int:participant_id>/download_qr")
def download_qr(participant_id):
    participant = Participant.get_by_id(participant_id)
    if not participant or not participant.get("qr_code_path"):
        flash("QR code file not found.", "danger")
        return redirect(url_for("participants.list_participants"))

    abs_path = QRGenerator.get_absolute_path(participant["qr_code_path"])
    if not abs_path.exists():
        # Regenerate if missing on disk
        QRGenerator.generate(
            participant_uuid=participant["participant_uuid"],
            registration_number=participant["registration_number"],
            participant_name=participant["name"],
            event_name=participant["event_name"]
        )

    return send_file(
        str(abs_path),
        as_attachment=True,
        download_name=f"QR_{participant['registration_number']}.png"
    )
