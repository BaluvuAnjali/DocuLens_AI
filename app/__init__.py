import os
from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from dotenv import load_dotenv
from werkzeug.exceptions import RequestEntityTooLarge

load_dotenv()

def create_app():
    app = Flask(__name__, static_folder="../frontend", static_url_path="")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_CONTENT_LENGTH_MB", "25")) * 1024 * 1024
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    from .routes import api
    app.register_blueprint(api, url_prefix="/api")
    @app.get("/")
    def home():
        return send_from_directory(app.static_folder, "index.html")
    @app.get("/api/health")
    def health():
        return jsonify({"status": "online", "service": "DocuLens AI", "version": "1.0.0"})

    @app.errorhandler(RequestEntityTooLarge)
    def too_large(_error):
        return jsonify({"error": "File is too large. Maximum upload size is " + os.getenv("MAX_CONTENT_LENGTH_MB", "25") + " MB."}), 413

    @app.errorhandler(404)
    def not_found(_error):
        if request.path.startswith("/api/"):
            return jsonify({"error": "API endpoint not found."}), 404
        return _error_page(404)

    @app.errorhandler(500)
    def internal_error(_error):
        app.logger.exception("Unhandled DocuLens server error")
        if request.path.startswith("/api/"):
            return jsonify({"error": "Unexpected server error. Check the PowerShell window for the full traceback."}), 500
        return "Unexpected server error. Check the server terminal.", 500
    os.makedirs("instance_data", exist_ok=True)
    return app

def _error_page(status):
    return ("Page not found.", status)
