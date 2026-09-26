# Internship analyzer backend

Flask API that compares a student's application materials with a job description
using OpenAI. Returns a `strong`, `moderate`, or `weak` rating, requirement-level
evidence and gaps, document-specific improvements, example revisions, and next steps.
This rating measures material alignment, not hiring probability. No frontend,
accounts, authentication, or database is included.

## Run locally

Requires Python 3.10+ (Render uses Python 3.13).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Set OPENAI_API_KEY in .env before analyzing materials.
flask --app app run --port 5000
```

Never commit `.env`. `OPENAI_MODEL` defaults to `gpt-4o-mini`; you can override it
with a model supporting Responses API Structured Outputs. `CORS_ORIGINS` is an
optional comma-separated list of exact frontend origins. Leave it empty for
same-origin/server-to-server use. Do not put the OpenAI key in frontend code.

## API

`GET /health` returns `{"status":"ok"}` without calling OpenAI. This is a
liveness check, not verification of API credentials or quota.

`POST /api/analyze` accepts `Content-Type: application/json`:

```json
{
  "resume": "Computer science student. Built a Python Flask app with a team of three.",
  "job_description": "Software engineering intern. Requires Python and SQL. Teamwork preferred.",
  "cover_letter": "I am interested in this internship because I enjoy developing backend services."
}
```

`resume` and `job_description` are required nonblank strings, limited to 30,000
and 20,000 characters. `cover_letter` is optional, limited to 15,000 characters;
omitted, null, or blank means absent. Fields are trimmed. Unknown fields and
non-string values are rejected. Maximum HTTP body size is 300,000 bytes.
Files and URLs are not fetched or parsed; send the actual document text.

```sh
curl http://localhost:5000/api/analyze \
  -H 'Content-Type: application/json' \
  -d '{"resume":"Built a Python Flask app.","job_description":"Python intern with SQL experience."}'
```

Example response (illustrative; AI wording and ratings vary):

```json
{
  "overall_score": "moderate",
  "summary": "Your Python project is relevant, but SQL experience is not demonstrated.",
  "score_reasoning": "One core requirement is supported, while another needs evidence.",
  "requirement_matches": [
    {"requirement":"Python","importance":"required","match":"met","evidence":"Resume: Built a Python Flask app.","gap":""},
    {"requirement":"SQL","importance":"required","match":"not_demonstrated","evidence":"Not demonstrated","gap":"No SQL project or coursework is described."}
  ],
  "resume_feedback": {
    "strengths": ["Names a relevant Python framework."],
    "improvements": [{
      "location":"Project description",
      "current_text":"Built a Python Flask app.",
      "issue":"The project's purpose and your contribution are unclear.",
      "suggested_change":"Explain the app's purpose and your specific contribution; include only true details.",
      "example_revision":"Built a Python Flask app to [purpose], implementing [specific feature]. Replace placeholders only with true details.",
      "priority":"high"
    }]
  },
  "cover_letter_feedback": null,
  "next_steps": ["Describe your Python project's purpose.","Add SQL coursework or project evidence if available.","Connect your experience directly to the internship requirements."]
}
```

`cover_letter_feedback` has the same shape as `resume_feedback` when supplied.
Requirement match values are `met`, `partial`, and `not_demonstrated`.
Improvement priorities are `high`, `medium`, and `low`. `current_text` can be null
for content that should be added. See `schemas.py` for the complete response schema.

Errors use `{"error":{"code":"...","message":"..."}}`, with field details
for validation failures. Statuses: 400 invalid JSON/fields, 413 body too large,
415 wrong content type, 422 model refusal, 502 provider/invalid-output failure,
503 missing credentials or provider quota/availability issues, 504 provider timeout.
Requests have a 60-second provider timeout with automatic retries disabled.

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, create a **Blueprint** and select the repository. `render.yaml`
   configures the Python service, Gunicorn command, and health check.
3. Set `OPENAI_API_KEY` in Render's environment settings. Set `CORS_ORIGINS` to
   your frontend origin when you have one (or leave empty).
4. Deploy, then request `https://YOUR-SERVICE.onrender.com/health` and send an
   analysis request to `https://YOUR-SERVICE.onrender.com/api/analyze`.

For a manual Web Service deployment, use build command
`pip install -r requirements.txt` and start command
`gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90`.
Set the health check path to `/health` and the same environment variables.

## Privacy and operating limits

The app does not persist submissions or results and does not log their content.
Documents are sent to OpenAI with `store=False`; this does not override OpenAI's
own data retention policies. Responses include `Cache-Control: no-store`.
The endpoint is public and unauthenticated as requested. Anyone who can access
it can generate billable API requests; CORS is not authentication or rate limiting.
Configure usage controls before broad public exposure. No distributed rate
limiter or job queue is included.

The prompt requests evidence-grounded feedback, but AI feedback still needs review.
Missing cover letters are not penalized. The rubric prioritizes core requirements
and credits student projects, coursework, and transferable experience.

## Tests

```sh
python -m pytest -q
```

Tests mock OpenAI and require no API key or paid requests. They cover input
validation, JSON errors, output handling, optional cover letters, provider failures,
privacy headers, and CORS. A live request with your Render key is still needed to
verify your account's model access and assess feedback quality.

References: [OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)
and [Render Flask deployment](https://render.com/docs/deploy-flask).
