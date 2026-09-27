# Internship analyzer backend

Flask API that compares a student's application materials with a job description
using OpenAI. Returns a `strong`, `moderate`, or `weak` rating, requirement-level, evidence and gaps, document-specific improvements, example revisions, and next steps.
The frontend is hosted separately on GitHub Pages. No accounts, authentication, or database is included.

- [Live frontend](https://irishaoru.github.io/internship-analyzer-frontend/)
- [Backend health check](https://internship-analyzer.onrender.com/health)
- [Frontend repository](https://github.com/irishaoru/internship-analyzer-frontend)

## How the frontend communicates with the backend

When a user fills in their resume and job description and clicks **Analyze my fit**, the HTML/CSS/JavaScript frontend validates the required fields, then uses `fetch()`
to send JSON in a `POST` request to
`https://internship-analyzer.onrender.com/api/analyze`.

The request contains `resume`, `job_description`, and optional `cover_letter`
(null when absent). The title and company fields are display labels and are not sent to the backend. The backend validates the request, calls OpenAI using its server-side key, and returns structured JSON.

The frontend displays the overall rating, summary, requirement evidence and gaps, resume and optional cover-letter feedback, and recommended next steps. While waiting, it shows a loading message. Invalid input, server errors, network failures, and request timeouts produce error messages. The frontend timeout is 150 seconds.
**Try an example** displays a local sample and does not call the backend.

Because GitHub Pages and Render use different origins, set this environment
variable on Render:

```env
CORS_ORIGINS=https://irishaoru.github.io
```

Use the origin only, without the `/internship-analyzer-frontend/` path. To also allow a local frontend, use a comma-separated value:
`https://irishaoru.github.io,http://localhost:8000`.

## Run locally

Requires Python 3.10+ (Render uses Python 3.13).

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
# Create .env in the backend folder with the values shown below.
flask --app app run --port 5000
```

Set these values in your local `.env` (replace the placeholder privately):

```env
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
CORS_ORIGINS=http://localhost:8000
```

The backend runs at `http://localhost:5000`. To connect a local copy of the
separate frontend, set its `config.js` `baseUrl` to `http://localhost:5000`, keep `endpoint: '/api/analyze'`, and serve that frontend with
`python3 -m http.server 8000`. Open `http://localhost:8000`.

Never commit `.env`. `OPENAI_MODEL` defaults to `gpt-4o-mini`; you can override it with a model supporting Responses API Structured Outputs. `CORS_ORIGINS` is an optional comma-separated list of exact frontend origins. Leave it empty for same-origin/server-to-server use. Do not put the OpenAI key in frontend code.

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

`resume` and `job_description` are required nonblank strings, limited to 30, 000 and 20,000 characters. `cover_letter` is optional, limited to 15,000 characters; omitted, null, or blank means absent. Fields are trimmed. Unknown fields and non-string values are rejected. Maximum HTTP body size is 300,000 bytes.
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
Improvement priorities are `high`, `medium`, and `low`. `current_text` can be null for content that should be added. See `schemas.py` for the complete response schema.

Errors use `{"error":{"code":"...","message":"..."}}`, with field details
for validation failures. Statuses: 400 invalid JSON/fields, 413 body too large, 415 wrong content type, 422 model refusal, 502 provider/invalid-output failure, 503 missing credentials or provider quota/availability issues, 504 provider timeout.
Requests have a 60-second provider timeout with automatic retries disabled.

## Deploy to Render

1. Push this repository to GitHub.
2. In Render, create a Web Service and connect the backend GitHub repository. 
3. Use build command `pip install -r requirements.txt` and start command 4. `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90`.
4. Add OPENAI_API_KEY and CORS_ORIGINS in Render’s environment settings
5. Set the health check path to `/health` and the same environment variables.

## Authentication and secrets

The application has no user login; `/api/analyze` is public and unauthenticated.
The OpenAI API key authenticates the backend's requests to OpenAI, not users of this application. Locally, `load_dotenv()` loads it from `.env`, which is excluded by `.gitignore`. In production, set `OPENAI_API_KEY` in Render's environment settings. Keep the real key out of GitHub, frontend JavaScript, and browser requests.
`OPENAI_MODEL` and `CORS_ORIGINS` are configuration values, not secrets.