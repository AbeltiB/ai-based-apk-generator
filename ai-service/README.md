@"
# AI Service

AI-powered mobile app generation service built with FastAPI and Anthropic Claude.

## Setup

1. Install dependencies:
``````bash
   poetry install
``````

2. Configure environment variables in `.env`

3. Run the service:
``````bash
   poetry run uvicorn app.main:app --reload
``````

## Development

- Python 3.13+
- Poetry for dependency management
- FastAPI for API framework
- Anthropic Claude for AI generation
- RabbitMQ for message queuing
- Redis for caching

## Testing
``````bash
poetry run pytest
``````
"@ | Out-File -FilePath README.md -Encoding utf8