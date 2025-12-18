# AI Service

AI-powered mobile app generation service using Claude API.

## Setup
```bash
# Install dependencies
poetry install

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run service
poetry run uvicorn app.main:app --reload
```

## Development
```bash
# Run tests
poetry run pytest

# Format code
poetry run black .

# Lint code
poetry run ruff check .
```

## Architecture

- FastAPI web framework
- Anthropic Claude API for AI generation
- RabbitMQ for message queuing
- Redis for caching