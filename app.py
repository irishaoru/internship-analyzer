import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from openai import (
    APIConnectionError, APIError, APITimeoutError, AuthenticationError,
    OpenAI, RateLimitError,
)
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException

from analyzer import AnalysisRefused, InvalidAnalysis, analyze
from schemas import AnalysisRequest


def create_app(config=None, openai_client=None):
    load_dotenv()
    app = Flask(__name__)
    app.config.from_mapping(
        MAX_CONTENT_LENGTH=300000,
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        CORS_ORIGINS=os.getenv("CORS_ORIGINS", ""),
    )
    if config:
        app.config.update(config)
    origins = [o.strip() for o in app.config["CORS_ORIGINS"].split(",") if o.strip()]
    if origins:
        CORS(app, resources={r"/api/*": {"origins": origins}},
             methods=["POST", "OPTIONS"], allow_headers=["Content-Type"])
    client = openai_client
    if client is None and app.config["OPENAI_API_KEY"]:
        client = OpenAI(api_key=app.config["OPENAI_API_KEY"], timeout=60, max_retries=0)

    def error(code, message, status, details=None):
        body = {"error": {"code": code, "message": message}}
        if details is not None:
            body["error"]["details"] = details
        return jsonify(body), status

    @app.after_request
    def no_cache(response):
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    @app.post("/api/analyze")
    def analyze_materials():
        if not request.is_json:
            return error("unsupported_media_type", "Use Content-Type: application/json.", 415)
        body = request.get_json()
        try:
            submission = AnalysisRequest.model_validate(body)
        except ValidationError as exc:
            details = [{"field": ".".join(map(str, e["loc"])), "message": e["msg"]}
                       for e in exc.errors(include_input=False, include_url=False)]
            return error("invalid_request", "Check the submitted fields.", 400, details)
        if client is None:
            return error("service_unconfigured", "The server's OpenAI API key is not configured.", 503)
        try:
            return jsonify(analyze(client, app.config["OPENAI_MODEL"], submission))
        except AnalysisRefused:
            return error("analysis_refused", "Unable to analyze these materials. Revise the input and try again.", 422)
        except RateLimitError:
            return error("provider_rate_limited", "The analysis service is busy or its quota is exhausted. Try again later.", 503)
        except APITimeoutError:
            return error("analysis_timeout", "The analysis timed out. Try again later.", 504)
        except AuthenticationError:
            return error("provider_configuration_error", "The analysis service credentials need attention.", 503)
        except APIConnectionError:
            return error("provider_unavailable", "The analysis service is temporarily unavailable.", 502)
        except (InvalidAnalysis, ValidationError, ValueError):
            return error("invalid_analysis", "The analysis service returned an incomplete or invalid result. Try again.", 502)
        except APIError:
            return error("provider_error", "The analysis service could not complete the request.", 502)

    @app.errorhandler(HTTPException)
    def http_error(exc):
        response = exc.get_response()
        response.data = app.json.dumps({"error": {
            "code": exc.name.lower().replace(" ", "_"), "message": exc.description,
        }})
        response.content_type = "application/json"
        return response

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        # Do not log exception bodies: upstream exceptions can contain personal data.
        app.logger.error("Unhandled error type: %s", type(exc).__name__)
        return error("internal_error", "An unexpected server error occurred.", 500)

    return app


app = create_app()
