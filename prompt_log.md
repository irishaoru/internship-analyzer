# AI Prompt Log

This log summarizes the AI tools and key prompts I used to develop the Internship Analyzer.

## Tools and models used

- **Tool:** Codex
- **Model:** GPT-6 Astra

<!-- Repeat the bullets above if you used more than one tool. -->

## Key prompts

### 1. Backend development

Initial prompt: build an internship analyzer for me where the user can input their resume and cover letter and website uses openAI API to determine how strongly the students' materials match the specific job description and returns them personalized feedback on where specifically to improve as well as an overall score of either strong, moderate or weak. build out just the backend of this so that i can deploy it on render.com. ask any quesitons you may have before proceeding

Other key prompts that shaped implementation: 
1. Please use:
Stack: Python + Flask 
Input format: JSON request body 
Output format: JSON response 
Accounts/auth: None 
Storage/database: None 
AI/API: OpenAI API 
Deployment: Render 
Secrets: Environment variables on Render

2. do i need to install any packages?

3. how do i run my backend locally before deplying to render?

4. can i even run it if i have no frontend code?

5. it says my port is already in use what should i do?

6. how do i submit a resume and job description locally?

7. how to delete something i wrote in my terminal?

8. unknown file attribute? what does this mean?

9. {"error":{"code":"service_unconfigured","message":"The server's OpenAI API key is not configured."}} - what is going on here?

10. for my start command on render, can i just put gunicorn.app:app? why do i need to do: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 90?

## Frontend 

Initial prompt: i've built out my backend and deployed it on render for my internship analyzer web application. now help me build out the frontend with HTML, CSS and JavaScript.

Other key prompts that shaped implementation:


### 2. Frontend and backend connection
1. wait i thought i was just hosting this through github pages and render woudl be running independently

2. why do i need to use CORS_ORIGINS? can't i just push to github and then just deploy direclty and see my site?

3. my professor said we could just serve both from a single rendor service? could i use that approach?

4. ok i'll use CORS then how do i do it?

5. do i add it under environment variables or linked environment groups?


### 3. Testing end-to-end
1. how do i do the empyt inputs and backend failures thingy?

