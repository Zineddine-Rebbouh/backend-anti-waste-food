<div align="center">

# SaveFood DZ / Tawfir — Backend API

Django REST API powering a three sided food waste marketplace in Algeria: merchants list surplus food, consumers buy it at a discount, and charities claim what's left as a donation.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-5.0-092E20?logo=django)](https://www.djangoproject.com/)
[![DRF](https://img.shields.io/badge/DRF-3.14-A30000)](https://www.django-rest-framework.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-PostGIS%20%2B%20pgvector-336791?logo=postgresql)](https://postgis.net/)
[![Redis](https://img.shields.io/badge/Redis-Celery%20broker-DC382D?logo=redis)](https://redis.io/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-4285F4?logo=google)](https://ai.google.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](#license)

</div>

<br>

## Overview

This is the backend for SaveFood DZ (internally also referred to as Tawfir), the API that the [Flutter mobile app](https://github.com/Zineddine-Rebbouh/anti_food_waste_app) and the admin dashboard both talk to. It is a Django monolith split into focused apps, built around one core loop: a merchant posts surplus food before it expires, a consumer or charity claims it, and the platform handles pricing, pickup, notifications, and impact tracking around that transaction.

Beyond basic CRUD, this backend does some genuinely interesting things: it runs a retrieval augmented support chatbot on top of Google Gemini and pgvector, a hybrid recommendation engine that blends spatial filtering with collaborative and content based scoring, an eco score system that rewards good platform behavior, and a route planning service that sequences a charity's pickups and pulls real road geometry from OSRM.

<br>

## Key Features

| Area | Description |
|---|---|
| Authentication | JWT based auth (`djangorestframework-simplejwt`) with role specific user types: consumer, merchant, charity |
| Listings | Surplus food listings with category, dietary tags, freshness grade, pricing, quantity, and pickup windows; geo search and filtering |
| Orders | Full order lifecycle (reserve, confirm, collect, cancel) modeled as an explicit state machine, with QR code based pickup confirmation |
| Donations | Charity facing donation requests and fulfillment, separate from paid orders |
| Route planning | `/orders/route-plan/` sequences a consumer or charity's pending pickups with a nearest neighbor heuristic and pulls real driving geometry from OSRM |
| AI support chat | Retrieval augmented chatbot (Gemini + pgvector embeddings) that answers platform questions from a knowledge base and escalates sensitive topics to a human |
| Recommendations | Hybrid engine combining PostGIS spatial candidate selection, collaborative filtering, and content based scoring, with support for sponsored listings |
| Eco score | Per user reputation score that moves up or down based on platform behavior (fulfilled orders, cancellations, donations, etc.), grouped into tiers |
| Reviews | Ratings and reviews for merchants and listings |
| Notifications | In app, email, and push notifications (Firebase Cloud Messaging) dispatched through Celery tasks |
| Billing | Merchant subscription plans and status (trial, active, past due, suspended, cancelled) gating what a merchant account can do |
| Live chat | WebSocket based chat between users via Django Channels, separate from the AI support bot |
| Analytics | Merchant dashboards and platform impact metrics, computed via scheduled aggregation tasks |
| API docs | Auto generated OpenAPI schema with Swagger UI and ReDoc |

<br>

## Tech Stack

**Core**
* [Python 3.11](https://www.python.org/) / [Django 5.0](https://www.djangoproject.com/)
* [Django REST Framework](https://www.django-rest-framework.org/) for the API layer
* [djangorestframework-simplejwt](https://django-rest-framework-simplejwt.readthedocs.io/) for JWT auth
* [django-filter](https://django-filter.readthedocs.io/) for queryset filtering
* [drf-spectacular](https://drf-spectacular.readthedocs.io/) for OpenAPI schema, Swagger, and ReDoc

**Data layer**
* [PostgreSQL 15](https://www.postgresql.org/) with [PostGIS](https://postgis.net/) for geographic queries and [pgvector](https://github.com/pgvector/pgvector) for embedding similarity search
* [Redis](https://redis.io/) for caching and as the Celery broker/result backend
* [psycopg](https://www.psycopg.org/) / `psycopg2-binary` as database drivers

**Async and realtime**
* [Celery](https://docs.celeryq.dev/) with [django-celery-beat](https://django-celery-beat.readthedocs.io/) for background jobs and scheduled tasks
* [Flower](https://flower.readthedocs.io/) for Celery monitoring
* [Django Channels](https://channels.readthedocs.io/) + [Daphne](https://github.com/django/daphne) for WebSocket based chat

**AI and search**
* [Google Generative AI SDK](https://ai.google.dev/) (Gemini) for the RAG support chatbot
* Custom embedding service + `pgvector` cosine distance search for knowledge base retrieval
* Custom hybrid recommendation engine (spatial + collaborative + content based scoring)

**Storage, ops, and infra**
* [MinIO](https://min.io/) (dev) / [AWS S3](https://aws.amazon.com/s3/) (prod) via `django-storages` and `boto3`
* [Sentry](https://sentry.io/) for error tracking
* [Firebase Admin SDK](https://firebase.google.com/docs/admin/setup) for push notifications
* [Gunicorn](https://gunicorn.org/) (prod WSGI) and Daphne (ASGI, for WebSockets)
* [Docker](https://www.docker.com/) / Docker Compose for local orchestration

**Testing and tooling**
* [pytest](https://docs.pytest.org/) / `pytest-django` / `pytest-cov` / `model-bakery` / `responses`
* [black](https://black.readthedocs.io/), [isort](https://pycqa.github.io/isort/), [flake8](https://flake8.pycqa.org/), [mypy](https://mypy-lang.org/) with `django-stubs`

<br>

## Project Structure

```
backend-anti-waste-food/
├── config/
│   ├── settings/              (base, development, staging, production, test)
│   ├── urls.py                (root URL configuration)
│   ├── asgi.py                (ASGI entry point, WebSocket routing)
│   ├── wsgi.py                (WSGI entry point)
│   └── celery.py              (Celery app configuration)
├── apps/
│   ├── core/                  (shared pagination, permissions, exceptions, middleware, geo utilities)
│   ├── users/                 (accounts, profiles, JWT auth, eco score engine)
│   ├── listings/              (surplus food listings, geo search, filters)
│   ├── orders/                (order lifecycle, state machine, route planning service)
│   ├── donations/             (charity donation requests and fulfillment)
│   ├── reviews/                (ratings and reviews)
│   ├── notifications/          (in app, email, push notification dispatch)
│   ├── chat/                    (AI support chatbot: retrieval, embeddings, Gemini integration; live chat consumers/routing)
│   ├── billing/                 (merchant subscription plans and status)
│   ├── recommendations/         (hybrid recommendation engine, feature scoring, caching)
│   └── analytics/               (merchant dashboards, impact metrics, scheduled aggregation)
├── scripts/                    (seeding, data fixes, and diagnostic scripts)
├── docs/
│   └── BACKEND_SETUP_AND_INTEGRATION.md   (detailed setup and integration guide)
├── docker-compose.yml           (Postgres/PostGIS, Redis, web, Celery worker/beat, Flower, MinIO)
├── docker-compose.prod.yml
├── Dockerfile
├── manage.py
├── pyproject.toml               (Poetry dependencies and tool config)
└── .env.example
```

Most apps follow the same internal shape: `models.py` for data, `serializers.py` for the API representation, `views.py` for endpoints, `permissions.py` for access rules, `services.py` for business logic that doesn't belong in a view or model, and `tasks.py` for anything that runs asynchronously via Celery.

<br>

## Architecture Notes

**Order lifecycle.** Orders move through an explicit state machine (`apps/orders/state_machine.py`) rather than ad hoc status checks, so valid transitions (reserve to confirmed to collected, or cancelled) are enforced in one place.

**Route planning.** `POST /api/v1/orders/route-plan/` takes a user's active orders and returns an ordered route. The core sequencing uses a nearest neighbor heuristic over haversine distance (no external API required for the ordering itself), then optionally enriches the result with real road geometry and driving time from the public OSRM routing service.

**AI support chat.** Incoming questions are checked against a list of escalation triggers (fraud, disputes, account issues, and similar) and routed to a human when needed. Otherwise, the message is embedded and matched against a `KnowledgeChunk` table using pgvector cosine distance, and the top matches are injected as context into a Gemini prompt that is instructed to answer only from that context.

**Recommendations.** The engine first builds a bounded candidate pool with a PostGIS spatial filter, then scores each candidate with several strategies (collaborative signal from `UserInteraction` history, content based similarity from a `UserProfile` vector, and others) that are fused by weighted sum, with support for injecting sponsored listings.

**Eco score.** User behavior (fulfilling orders, cancelling, donating, etc.) applies score deltas defined per user type, clamped to a min/max range and mapped to named tiers.

<br>

## Getting Started

### Prerequisites

* [Docker](https://www.docker.com/) and Docker Compose (recommended), or Python 3.11+ with PostgreSQL (with PostGIS and pgvector extensions) and Redis installed locally
* A [Google Gemini API key](https://ai.google.dev/) for the AI support chat
* A [Firebase](https://firebase.google.com/) service account for push notifications (optional for local development)

### Option A: Run with Docker Compose (recommended)

```bash
git clone https://github.com/Zineddine-Rebbouh/backend-anti-waste-food.git
cd backend-anti-waste-food

cp .env.example .env
# Edit .env and set SECRET_KEY, GEMINI_API_KEY, and any other values you need

docker compose up --build
```

This starts Postgres/PostGIS, Redis, the Django app, a Celery worker, Celery Beat, Flower, and MinIO. The API will be available at `http://localhost:8080/`.

### Option B: Run locally without Docker

```bash
git clone https://github.com/Zineddine-Rebbouh/backend-anti-waste-food.git
cd backend-anti-waste-food

python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

pip install poetry
poetry install

cp .env.example .env
# Point DATABASE_URL and REDIS_URL at your local Postgres/Redis instances,
# and set SECRET_KEY and GEMINI_API_KEY

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8080
```

To run background jobs locally, start a Celery worker and beat scheduler in separate terminals:

```bash
celery -A config worker -l INFO
celery -A config beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Environment variables

See `.env.example` for the full list. At minimum you'll need to set:

```bash
SECRET_KEY=
DJANGO_SETTINGS_MODULE=config.settings.development
DATABASE_URL=postgresql://savefood_user:savefood_pass@localhost:5432/savefood_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
GEMINI_API_KEY=
```

> Note: rotate any API key that has ever been committed to version control before using this project. Never commit real secrets in `.env`.

<br>

## API Documentation

Once the server is running, interactive API docs are available at:

* `/api/docs/` — Swagger UI
* `/api/redoc/` — ReDoc
* `/api/schema/` — raw OpenAPI schema

Health checks live at `/health/`.

<br>

## Testing

```bash
pytest
```

Test configuration lives in `pytest.ini`, with `pytest-django`, `pytest-cov`, and `model-bakery` available for fixtures and factories.

<br>

## Further Reading

`docs/BACKEND_SETUP_AND_INTEGRATION.md` has a deeper walkthrough of the architecture, environment configuration, database setup, and how the Flutter app and admin dashboard integrate with this API.

<br>

## Roadmap Ideas

* [ ] CI pipeline running lint, type checks, and the test suite on every push
* [ ] Formal API versioning strategy beyond `/api/v1/`
* [ ] Expanded automated test coverage for the recommendation and route planning services
* [ ] Production deployment guide (Nginx, Gunicorn/Daphne, TLS)

<br>

## Contributing

Contributions, issues, and feature requests are welcome.

1. Fork the project
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

<br>

## License

This project is licensed under the MIT License.

<br>

## Author

**Zineddine Rebbouh**
GitHub: [@Zineddine-Rebbouh](https://github.com/Zineddine-Rebbouh)

</div>
