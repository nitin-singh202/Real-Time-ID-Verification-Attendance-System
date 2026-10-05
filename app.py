import logging
import sys
from pathlib import Path
from flask import Flask, render_template, send_from_directory
from config import Config
from database.db import db
from routes.dashboard import dashboard_bp
from routes.participants import participants_bp
from routes.scanner import scanner_bp
from routes.attendance import attendance_bp
from routes.events import events_bp
from routes.reports import reports_bp

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(Config.LOGS_DIR / "app.log", encoding="utf-8") if Config.LOGS_DIR.exists() else logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("attendance_system")


def create_app() -> Flask:
    """Application factory for ID Verification & Attendance System."""
    Config.init_app()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize Database tables
    try:
        db.init_db()
        logger.info(f"Database initialized with [{db.engine_type.upper()}] engine.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Register Blueprints
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(participants_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(reports_bp)

    # Route to serve generated QR code images
    @app.route("/data/qr_codes/<path:filename>")
    def serve_qr_code(filename):
        return send_from_directory(str(Config.QR_CODES_DIR), filename)

    # Global Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template("base.html", error_title="404 - Page Not Found", error_message="The requested page could not be located."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal Server Error: {e}")
        return render_template("base.html", error_title="500 - Server Error", error_message="An internal error occurred. Please check server logs."), 500

    return app


app = create_app()

if __name__ == "__main__":
    logger.info("Starting Real-Time ID Verification & Attendance System server...")
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
