from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError, AuthenticationError, RateLimitError
from openai import OpenAI

from app import create_app
from schemas import AnalysisResult


@pytest.fixture
def setup():
    result = AnalysisResult(
        overall_score="moderate", summary="Relevant project experience.",
        score_reasoning="Python is demonstrated; SQL is not demonstrated.",
        requirement_matches=[dict(requirement="Python", importance="required",
                                 match="met", evidence="Resume: Built a Python app.", gap="")],
        resume_feedback=dict(strengths=["Relevant project"], improvements=[]),
        cover_letter_feedback=None, next_steps=["Describe SQL experience if applicable."],
    )
    provider = Mock()
    provider.responses.parse.return_value = SimpleNamespace(
        status="completed", output=[], output_parsed=result)
    app = create_app({"TESTING": True, "CORS_ORIGINS": "https://frontend.example"}, provider)
    return app.test_client(), provider


PAYLOAD = {"resume": "Built a Python app.", "job_description": "Python and SQL internship."}


def test_analysis_and_provider_contract(setup):
    client, provider = setup
    response = client.post("/api/analyze", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json["overall_score"] == "moderate"
    assert response.json["cover_letter_feedback"] is None
    assert response.headers["Cache-Control"] == "no-store"
    args = provider.responses.parse.call_args.kwargs
    assert args["store"] is False
    assert args["text_format"] is AnalysisResult
    assert "Built a Python app." in args["input"][0]["content"]


def test_cover_letter(setup):
    client, provider = setup
    provider.responses.parse.return_value.output_parsed.cover_letter_feedback = (
        provider.responses.parse.return_value.output_parsed.resume_feedback)
    response = client.post("/api/analyze", json={**PAYLOAD, "cover_letter": "I built a Python app."})
    assert response.status_code == 200
    assert response.json["cover_letter_feedback"] is not None


@pytest.mark.parametrize("body", [None, [], {}, {**PAYLOAD, "resume": "  "},
    {**PAYLOAD, "resume": 123}, {**PAYLOAD, "cover_letter": []},
    {**PAYLOAD, "extra": "ignored?"}, {**PAYLOAD, "resume": "a" * 30001},
    {**PAYLOAD, "job_description": "a" * 20001}, {**PAYLOAD, "cover_letter": "a" * 15001}])
def test_invalid_input_does_not_call_provider(setup, body):
    client, provider = setup
    response = client.post("/api/analyze", json=body, content_type="application/json")
    assert response.status_code == 400
    assert "error" in response.json
    provider.responses.parse.assert_not_called()


@pytest.mark.parametrize("letter", [None, "", "  "])
def test_empty_optional_letter(setup, letter):
    client, _ = setup
    response = client.post("/api/analyze", json={**PAYLOAD, "cover_letter": letter})
    assert response.status_code == 200
    assert response.json["cover_letter_feedback"] is None


def test_http_errors(setup):
    client, provider = setup
    cases = [client.post("/api/analyze", data="text"),
             client.post("/api/analyze", data="{broken", content_type="application/json"),
             client.post("/api/analyze", data="x" * 300001, content_type="application/json"),
             client.get("/missing"), client.get("/api/analyze")]
    assert [r.status_code for r in cases] == [415, 400, 413, 404, 405]
    assert all("error" in r.json for r in cases)
    provider.responses.parse.assert_not_called()


def test_missing_key_and_health():
    client = create_app({"TESTING": True, "OPENAI_API_KEY": ""}).test_client()
    assert client.get("/health").json == {"status": "ok"}
    assert client.post("/api/analyze", json=PAYLOAD).status_code == 503


@pytest.mark.parametrize("kind,status", [("timeout", 504), ("connection", 502),
                                         ("auth", 503), ("rate", 503)])
def test_provider_errors_are_redacted(setup, kind, status):
    client, provider = setup
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(429 if kind == "rate" else 401, request=request)
    errors = {
        "timeout": APITimeoutError(request=request),
        "connection": APIConnectionError(request=request),
        "auth": AuthenticationError("secret upstream detail", response=response, body=None),
        "rate": RateLimitError("secret upstream detail", response=response, body=None),
    }
    provider.responses.parse.side_effect = errors[kind]
    result = client.post("/api/analyze", json=PAYLOAD)
    assert result.status_code == status
    assert "secret" not in result.get_data(as_text=True)


@pytest.mark.parametrize("kind,status", [("incomplete", 502), ("missing", 502),
                                         ("refusal", 422), ("missing_letter", 502)])
def test_invalid_model_results(setup, kind, status):
    client, provider = setup
    response = provider.responses.parse.return_value
    payload = dict(PAYLOAD)
    if kind == "incomplete":
        response.status = "incomplete"
    elif kind == "missing":
        response.output_parsed = None
    elif kind == "refusal":
        response.output = [SimpleNamespace(content=[SimpleNamespace(type="refusal")])]
    else:
        payload["cover_letter"] = "My cover letter."
    assert client.post("/api/analyze", json=payload).status_code == status


def test_cors_preflight(setup):
    client, provider = setup
    response = client.options("/api/analyze", headers={
        "Origin": "https://frontend.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"})
    assert response.headers["Access-Control-Allow-Origin"] == "https://frontend.example"
    blocked = client.options("/api/analyze", headers={"Origin": "https://other.example"})
    assert "Access-Control-Allow-Origin" not in blocked.headers
    provider.responses.parse.assert_not_called()


def test_real_sdk_serialization_and_parsing(setup):
    import json

    _, provider = setup
    result = provider.responses.parse.return_value.output_parsed.model_dump()

    def handler(request):
        body = json.loads(request.content)
        assert body["store"] is False
        assert body["text"]["format"]["type"] == "json_schema"
        assert body["text"]["format"]["strict"] is True
        return httpx.Response(200, json={
            "id": "resp_test", "object": "response", "created_at": 0,
            "status": "completed", "model": "gpt-4o-mini",
            "output": [{"id": "msg_test", "type": "message", "role": "assistant",
                        "status": "completed", "content": [{"type": "output_text",
                        "text": json.dumps(result), "annotations": []}]}],
        })

    with OpenAI(api_key="test-key", http_client=httpx.Client(
        transport=httpx.MockTransport(handler))) as sdk:
        client = create_app({"TESTING": True}, sdk).test_client()
        response = client.post("/api/analyze", json=PAYLOAD)
        assert response.status_code == 200
        assert response.json == result
