# PicVibez Smart Event Gallery - Backend API

Production-grade FastAPI backend for PicVibez, a smart event photo gallery with AI-powered face recognition, semantic search, and real-time collaboration.

## Architecture

- **FastAPI** on **AWS EC2** -- API orchestrator
- **Supabase** -- Auth, PostgreSQL (RLS), Realtime
- **AWS S3 + CloudFront** -- Media storage and CDN delivery
- **AWS Lambda + SQS** -- Async image processing pipeline
- **AWS Rekognition** -- Face detection and clustering
- **Google Gemini** -- Semantic photo labeling
- **Stripe** -- Payment processing

## Quick Start

```bash
# 1. Clone and enter
cd picvibez-smart-event-gallery-server

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 5. Run dev server
uvicorn app.main:app --reload --port 10000
```

## Docker

```bash
# Development (with hot-reload)
docker-compose up

# Production build
docker build -t picvibez-server .
docker run -p 80:10000 --env-file .env picvibez-server
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:10000/docs
- ReDoc: http://localhost:10000/redoc

## Database Migrations

SQL migrations are in `supabase/migrations/`. Run them in order against your Supabase project:

```bash
# Using Supabase CLI
supabase db push
```

## Testing

```bash
pip install pytest httpx
pytest tests/ -v
```

## Project Structure

```
app/
  main.py              # FastAPI app, middleware, routes
  core/                # Config, security, dependency injection
  api/v1/              # Route modules (12 modules)
  models/              # Pydantic schemas and enums
  services/            # Business logic layer
  integrations/        # External service clients
  middleware/           # Rate limiting
lambdas/               # AWS Lambda handlers
edge_functions/        # Supabase Edge Functions
supabase/migrations/   # PostgreSQL schema + RLS + triggers
tests/                 # Pytest test suite
```
