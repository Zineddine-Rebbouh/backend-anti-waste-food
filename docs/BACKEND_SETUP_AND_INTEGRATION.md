# SaveFood DZ — Backend Setup & Integration Guide

> **Audience:** Backend engineers, mobile integrators, DevOps.
> **Purpose:** Complete reference for configuring, running, and connecting the SaveFood DZ backend so that it can communicate with the Flutter mobile application and the Django Admin dashboard.
> This document describes **what to configure and why** — not the implementation code itself.

---

## Table of Contents

1. [Backend Architecture Overview](#1-backend-architecture-overview)
2. [Environment Configuration](#2-environment-configuration)
3. [Database Setup](#3-database-setup)
4. [API Structure](#4-api-structure)
5. [File Storage](#5-file-storage)
6. [Running the Backend Locally](#6-running-the-backend-locally)
7. [Connecting the Flutter Mobile App](#7-connecting-the-flutter-mobile-app)
8. [Connecting the Admin Dashboard](#8-connecting-the-admin-dashboard)
9. [Development Best Practices](#9-development-best-practices)

---

## 1. Backend Architecture Overview

### Core Stack

| Layer          | Technology                        | Responsibility                                   |
| -------------- | --------------------------------- | ------------------------------------------------ |
| API Framework  | Django 5.0 + DRF 3.14             | REST endpoints, serialization, permissions       |
| Database       | PostgreSQL 15 + PostGIS           | Relational data + geographic queries             |
| Cache          | Redis 7                           | Response caching, session store                  |
| Task Queue     | Celery 5.3 + Redis broker         | Async jobs (notifications, QR expiry, analytics) |
| Task Schedule  | Celery Beat + DatabaseScheduler   | Periodic tasks (listing expiry, daily reports)   |
| File Storage   | MinIO (dev) / AWS S3 (prod)       | All uploaded media (photos, logos)               |
| Reverse Proxy  | Nginx (prod only)                 | TLS termination, static/media routing            |
| WSGI Server    | Gunicorn (prod)                   | Production Python process manager                |
| Error Tracking | Sentry                            | Exception capture & performance tracing          |
| API Docs       | drf-spectacular (Swagger + ReDoc) | Auto-generated interactive API documentation     |

### Django Application Layout

The project is structured as a Django monolith with eight focused apps, all under `apps/`:

```
config/              ← Django project config (settings, urls, celery, wsgi/asgi)
apps/
  core/              ← Shared utilities: pagination, permissions, exceptions, middleware
  users/             ← User accounts, profiles, JWT authentication, merchant/charity extensions
  listings/          ← Surplus food listings CRUD, geo search, availability management
  orders/            ← Order lifecycle (reserve → confirmed → collected/cancelled), QR codes
  donations/         ← Charity donation requests and fulfillment
  reviews/           ← Ratings and reviews for merchants and listings
  notifications/     ← In-app + email + SMS notification dispatch
  analytics/         ← Merchant dashboards, impact metrics, aggregation tasks
```

### Settings Environments

| Module                        | Use case                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------- |
| `config.settings.development` | Local development — relaxed security, console email, SQLite-compatible debug settings |
| `config.settings.staging`     | Pre-production — production security rules, SSL offloaded to load balancer            |
| `config.settings.production`  | Full HTTPS, S3 storage, Sentry, strict headers                                        |

The active settings module is controlled by the `DJANGO_SETTINGS_MODULE` environment variable.

### How Components Connect

```
Flutter Mobile App
       │  HTTPS + JWT Bearer token
       ▼
  [Nginx / dev: runserver]  ← port 80/443 (prod) or 8000 (dev)
       │
  Django REST API  /api/v1/*
       │
  ┌────┴────────────┐
  │   PostgreSQL    │  Primary data store, PostGIS for location data
  │   Redis         │  Cache layer + Celery message broker
  │   Celery Worker │  Async tasks triggered by API actions
  │   MinIO / S3    │  Media file storage
  └─────────────────┘
       │
  Django Admin  /admin/*   ← browser-based staff/superuser interface
```

---

## 2. Environment Configuration

All configuration is injected via environment variables. Never hard-code secrets in settings files. In development, copy `.env.example` to `.env` at the project root. In production, use Docker secrets or your hosting provider's secrets management.

### Core Django Variables

| Variable                 | Example Value                            | Purpose                                                                                                        |
| ------------------------ | ---------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| `SECRET_KEY`             | `django-insecure-...`                    | Cryptographic signing for sessions, CSRF, and tokens. Must be at least 50 random characters. Rotate if leaked. |
| `DJANGO_SETTINGS_MODULE` | `config.settings.development`            | Selects which settings module Django loads. Switch to `production` for deployments.                            |
| `DEBUG`                  | `True` / `False`                         | Enables detailed error pages and SQL logging. **Must be `False` in production.**                               |
| `ALLOWED_HOSTS`          | `localhost,127.0.0.1,api.savefood.dz`    | Comma-separated list of hostnames that Django will serve. Prevents host-header injection attacks.              |
| `ENVIRONMENT`            | `development` / `staging` / `production` | Sent to Sentry as the environment tag.                                                                         |

### Database

| Variable       | Example Value                                       | Purpose                                                                                   |
| -------------- | --------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `DATABASE_URL` | `postgresql://user:pass@localhost:5432/savefood_db` | Full DSN parsed by `dj-database-url`. Supports PostGIS engine automatically via settings. |

### Cache & Async

| Variable                | Example Value              | Purpose                                                                      |
| ----------------------- | -------------------------- | ---------------------------------------------------------------------------- |
| `REDIS_URL`             | `redis://localhost:6379/0` | Django cache backend. Database `0` reserved for cache.                       |
| `CELERY_BROKER_URL`     | `redis://localhost:6379/0` | Celery task queue broker. Shares Redis with cache.                           |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Where Celery stores task results. Database `1` keeps it separate from cache. |

### File Storage

| Variable                  | Example Value           | Purpose                                                          |
| ------------------------- | ----------------------- | ---------------------------------------------------------------- |
| `USE_S3`                  | `False` / `True`        | When `True`, switches media storage from local disk to S3/MinIO. |
| `AWS_ACCESS_KEY_ID`       | `minioadmin`            | S3 or MinIO access key.                                          |
| `AWS_SECRET_ACCESS_KEY`   | `minioadmin`            | S3 or MinIO secret key.                                          |
| `AWS_STORAGE_BUCKET_NAME` | `savefood-media`        | The bucket where all media files are uploaded.                   |
| `AWS_S3_ENDPOINT_URL`     | `http://localhost:9000` | Override for MinIO in development. Leave empty for real AWS S3.  |
| `AWS_S3_REGION_NAME`      | `us-east-1`             | AWS region. Required even for MinIO.                             |
| `AWS_S3_CUSTOM_DOMAIN`    | `cdn.savefood.dz`       | Optional CDN domain for serving media via a custom URL.          |

### Email

| Variable              | Example Value                                    | Purpose                                                                           |
| --------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------- |
| `EMAIL_BACKEND`       | `django.core.mail.backends.console.EmailBackend` | In development, prints emails to terminal. In production, change to SMTP backend. |
| `EMAIL_HOST`          | `smtp.sendgrid.net`                              | SMTP server hostname.                                                             |
| `EMAIL_PORT`          | `587`                                            | SMTP port. Use 587 for TLS (STARTTLS).                                            |
| `EMAIL_USE_TLS`       | `True`                                           | Enables STARTTLS encryption.                                                      |
| `EMAIL_HOST_USER`     | `apikey`                                         | SMTP username. For SendGrid, literally the string `apikey`.                       |
| `EMAIL_HOST_PASSWORD` | `SG.xxxx`                                        | SMTP password / API key.                                                          |
| `DEFAULT_FROM_EMAIL`  | `noreply@savefood.dz`                            | Sender address shown to recipients.                                               |

### SMS

| Variable                    | Example Value   | Purpose                                          |
| --------------------------- | --------------- | ------------------------------------------------ |
| `SMS_PROVIDER`              | `twilio`        | Notification backend selector.                   |
| `SMS_PROVIDER_ACCOUNT_SID`  | `ACxxxxxxxx`    | Twilio account identifier.                       |
| `SMS_PROVIDER_AUTH_TOKEN`   | `xxxxxxxx`      | Twilio authentication token.                     |
| `SMS_PROVIDER_PHONE_NUMBER` | `+213XXXXXXXXX` | The outbound phone number shown on received SMS. |

### Authentication (JWT)

| Variable                            | Example Value | Purpose                                                                                  |
| ----------------------------------- | ------------- | ---------------------------------------------------------------------------------------- |
| `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` | `60`          | How long an access token is valid. Short-lived for security.                             |
| `JWT_REFRESH_TOKEN_LIFETIME_DAYS`   | `30`          | How long a refresh token is valid. User stays logged in without re-entering credentials. |

### Security & Monitoring

| Variable               | Example Value               | Purpose                                                                                               |
| ---------------------- | --------------------------- | ----------------------------------------------------------------------------------------------------- |
| `SENTRY_DSN`           | `https://xxx@sentry.io/xxx` | Sentry project DSN. Leave empty to disable.                                                           |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000`     | Browser origins allowed to make cross-origin requests (admin dashboard). Mobile apps do not use CORS. |
| `FRONTEND_URL`         | `http://localhost:3000`     | Base URL for email links (password reset, verification).                                              |

### Rate Limiting

| Variable           | Example Value | Purpose                                                    |
| ------------------ | ------------- | ---------------------------------------------------------- |
| `RATELIMIT_ENABLE` | `True`        | Master switch for API rate limiting.                       |
| `AUTH_RATELIMIT`   | `5/15m`       | Max authentication attempts — prevents brute-force logins. |
| `API_RATELIMIT`    | `100/m`       | General API rate cap per user per minute.                  |

---

## 3. Database Setup

### Why PostgreSQL + PostGIS

The application uses **geographic search** (find listings near a GPS coordinate). Standard PostgreSQL cannot perform efficient spatial queries. PostGIS adds geometry data types and spatial indexes that make queries like "listings within 2 km of the user" performant at scale. The Django setting `django.contrib.gis.db.backends.postgis` enables this.

### Installation Options

**Option A — Docker (recommended for development)**

The `docker-compose.yml` file already defines a `db` service using the official `postgis/postgis:15-3.3` image. No manual installation needed. Start with `docker compose up db`.

**Option B — Native installation**

1. Install PostgreSQL 15 from your OS package manager.
2. Install the `postgis` extension package (e.g., `postgresql-15-postgis-3` on Ubuntu).
3. Create the database and user:

```sql
CREATE USER savefood_user WITH PASSWORD 'savefood_pass';
CREATE DATABASE savefood_db OWNER savefood_user;
\c savefood_db
CREATE EXTENSION postgis;
CREATE EXTENSION postgis_topology;
```

4. Verify PostGIS is active:

```sql
SELECT PostGIS_Version();
```

### Django Database Configuration

The `DATABASE_URL` environment variable is the single source of truth. The settings file parses it with `dj-database-url` and sets the engine to `django.contrib.gis.db.backends.postgis` automatically.

Format: `postgresql://USER:PASSWORD@HOST:PORT/DBNAME`

Example for local development: `postgresql://savefood_user:savefood_pass@localhost:5432/savefood_db`

Inside Docker Compose, the host is the service name: `postgresql://savefood_user:savefood_pass@db:5432/savefood_db`

### Migrations Workflow

Django migrations track changes to models and apply them to the database schema. The migration files live in each app's `migrations/` directory.

**Generating migrations** (after changing a model file):

```bash
python manage.py makemigrations
```

This creates timestamped migration files. Always commit these files to version control.

**Applying migrations** (on first setup or after pulling new code):

```bash
python manage.py migrate
```

This creates or updates all database tables, including PostGIS geometry columns.

**Checking migration status:**

```bash
python manage.py showmigrations
```

**Important:** Never manually edit the database schema. All schema changes must go through migration files.

### Data Model Summary

Below is the conceptual relationship between the eight apps and their primary data:

| App             | Core Models                                  | Key Relationships                                              |
| --------------- | -------------------------------------------- | -------------------------------------------------------------- |
| `users`         | `User`, `MerchantProfile`, `CharityProfile`  | User has a role; one-to-one extension profiles                 |
| `listings`      | `Listing`, `ListingImage`, `ListingCategory` | Listing belongs to a Merchant; has images and a category       |
| `orders`        | `Order`, `QRCode`                            | Order placed by Consumer against a Listing; QR code for pickup |
| `donations`     | `Donation`, `DonationClaim`                  | Donation created by Merchant; claimed by Charity               |
| `reviews`       | `Review`                                     | Left by Consumer on a completed Order; linked to Merchant      |
| `notifications` | `Notification`                               | Sent to any User; has delivery channel (in-app, email, SMS)    |
| `analytics`     | `DailyMetric`, `ImpactReport`                | Aggregated stats per Merchant and per platform day             |
| `core`          | _(no primary models)_                        | Shared base model classes, helpers                             |

**Geographic fields:** `Listing.location` and `MerchantProfile.location` are PostGIS `PointField` columns. They store longitude/latitude as geometry and support distance-based filtering.

---

## 4. API Structure

All API endpoints are mounted under the `/api/v1/` prefix. This allows future non-breaking evolution via `/api/v2/`.

### Endpoint Groups

#### `/api/v1/auth/` — Authentication

Handled by the `users` app and `djangorestframework-simplejwt`.

| Method  | Path                                   | Description                                               |
| ------- | -------------------------------------- | --------------------------------------------------------- |
| POST    | `/api/v1/auth/register/`               | Create a new account (consumer, merchant, or charity)     |
| POST    | `/api/v1/auth/login/`                  | Exchange credentials for JWT access + refresh tokens      |
| POST    | `/api/v1/auth/token/refresh/`          | Exchange a valid refresh token for a new access token     |
| POST    | `/api/v1/auth/logout/`                 | Blacklist the refresh token (invalidates the session)     |
| POST    | `/api/v1/auth/password/reset/`         | Initiate password reset via email                         |
| POST    | `/api/v1/auth/password/reset/confirm/` | Complete password reset with token from email             |
| GET/PUT | `/api/v1/users/me/`                    | Get or update the authenticated user's profile            |
| GET/PUT | `/api/v1/users/me/merchant-profile/`   | Merchant-specific profile (business name, logo, location) |
| GET/PUT | `/api/v1/users/me/charity-profile/`    | Charity-specific profile (org name, documents)            |

---

#### `/api/v1/listings/` — Surplus Food Listings

Handled by the `listings` app. Public reading, authenticated writing.

| Method    | Path                            | Description                                                              |
| --------- | ------------------------------- | ------------------------------------------------------------------------ |
| GET       | `/api/v1/listings/`             | List active listings (filterable by category, price, distance, merchant) |
| POST      | `/api/v1/listings/`             | Create a new listing (Merchant only)                                     |
| GET       | `/api/v1/listings/{id}/`        | Retrieve full listing detail                                             |
| PUT/PATCH | `/api/v1/listings/{id}/`        | Update a listing (owner Merchant only)                                   |
| DELETE    | `/api/v1/listings/{id}/`        | Remove a listing (owner Merchant only)                                   |
| GET       | `/api/v1/listings/nearby/`      | Geographic search — returns listings within radius of `lat,lng`          |
| GET       | `/api/v1/listings/categories/`  | List all listing categories                                              |
| POST      | `/api/v1/listings/{id}/images/` | Upload image(s) to a listing                                             |

**Key query parameters for `/api/v1/listings/`:**

- `lat`, `lng`, `radius_km` — geographic filter
- `category` — filter by category slug
- `min_price`, `max_price` — price range
- `available_only=true` — exclude sold-out listings
- `cursor` — pagination cursor (cursor-based pagination, 20 items per page)

---

#### `/api/v1/orders/` — Order Management

Handled by the `orders` app.

| Method | Path                           | Description                                        |
| ------ | ------------------------------ | -------------------------------------------------- |
| POST   | `/api/v1/orders/`              | Place an order on a listing (Consumer only)        |
| GET    | `/api/v1/orders/`              | List the authenticated user's orders               |
| GET    | `/api/v1/orders/{id}/`         | Order detail including QR code                     |
| POST   | `/api/v1/orders/{id}/cancel/`  | Cancel a pending order (Consumer)                  |
| POST   | `/api/v1/orders/{id}/confirm/` | Confirm order is ready for pickup (Merchant)       |
| POST   | `/api/v1/orders/{id}/collect/` | Mark order as collected via QR scan (Merchant)     |
| POST   | `/api/v1/orders/{id}/no-show/` | Mark consumer as no-show (Merchant)                |
| GET    | `/api/v1/orders/{id}/qr/`      | Retrieve the QR code image for pickup verification |

**Order state machine:**
`pending` → `confirmed` → `collected` (terminal, success)
`pending` → `cancelled` (terminal, by consumer or timeout)
`confirmed` → `no_show` (terminal, by merchant)

---

#### `/api/v1/donations/` — Food Donations

Handled by the `donations` app.

| Method | Path                               | Description                                        |
| ------ | ---------------------------------- | -------------------------------------------------- |
| GET    | `/api/v1/donations/`               | List available donations (filterable by proximity) |
| POST   | `/api/v1/donations/`               | Create a donation offer (Merchant only)            |
| GET    | `/api/v1/donations/{id}/`          | Donation detail                                    |
| PATCH  | `/api/v1/donations/{id}/`          | Update donation details (owner Merchant)           |
| POST   | `/api/v1/donations/{id}/claim/`    | Claim a donation (Charity only)                    |
| POST   | `/api/v1/donations/{id}/complete/` | Mark donation as transferred (Merchant or Charity) |

---

#### `/api/v1/reviews/` — Ratings & Reviews

Handled by the `reviews` app.

| Method | Path                              | Description                                            |
| ------ | --------------------------------- | ------------------------------------------------------ |
| GET    | `/api/v1/reviews/`                | List reviews (filter by `merchant_id` or `listing_id`) |
| POST   | `/api/v1/reviews/`                | Submit a review (Consumer only, on a completed order)  |
| GET    | `/api/v1/reviews/{id}/`           | Review detail                                          |
| DELETE | `/api/v1/reviews/{id}/`           | Delete own review (Consumer) or any review (Admin)     |
| GET    | `/api/v1/merchants/{id}/reviews/` | All reviews for a specific merchant                    |

---

#### `/api/v1/notifications/` — Notifications

Handled by the `notifications` app.

| Method | Path                                  | Description                                             |
| ------ | ------------------------------------- | ------------------------------------------------------- |
| GET    | `/api/v1/notifications/`              | List the user's notifications (paginated, newest first) |
| POST   | `/api/v1/notifications/{id}/read/`    | Mark a single notification as read                      |
| POST   | `/api/v1/notifications/read-all/`     | Mark all notifications as read                          |
| GET    | `/api/v1/notifications/unread-count/` | Count of unread notifications (for badge display)       |

---

#### `/api/v1/analytics/` — Analytics & Impact

Handled by the `analytics` app. Merchant and Admin roles only.

| Method | Path                                | Description                                                         |
| ------ | ----------------------------------- | ------------------------------------------------------------------- |
| GET    | `/api/v1/analytics/merchant/`       | Authenticated merchant's dashboard stats (orders, revenue, ratings) |
| GET    | `/api/v1/analytics/merchant/trend/` | Daily trend data for charts (filterable by `days=7/30/90`)          |
| GET    | `/api/v1/analytics/impact/`         | Platform-wide impact report (meals saved, CO2 equivalent)           |
| GET    | `/api/v1/analytics/admin/`          | Aggregated platform stats (Admin only)                              |

---

#### `/admin/` — Django Admin Interface

Browser-based admin panel for staff and superusers. Not a REST API — it is server-rendered HTML. Accessed at `http://localhost:8000/admin/` in development.

---

#### `/api/docs/` — Interactive API Documentation

Swagger UI auto-generated from the codebase. Available at `http://localhost:8000/api/docs/` in development. Also accessible as ReDoc at `/api/redoc/` and as raw OpenAPI schema JSON at `/api/schema/`.

---

#### `/health/` — Health Check

Returns HTTP 200 with a JSON body confirming the API is alive. Used by Docker health checks and load balancers.

---

## 5. File Storage

### What Is Stored

| Category              | Examples                        | Typical Size                        |
| --------------------- | ------------------------------- | ----------------------------------- |
| Merchant logos        | Shop logo, banner image         | Up to 2 MB per file                 |
| Listing photos        | Food images per listing         | Up to 5 MB per file, up to 5 images |
| Charity impact photos | Impact reports, donation photos | Up to 5 MB per file                 |
| User profile photos   | Consumer and staff avatars      | Up to 1 MB per file                 |

All files are images. The backend uses `Pillow` for validation and resizing, and `python-magic` to verify file MIME types beyond just the file extension.

### Development: Local Storage

When `USE_S3=False` (the default for development), Django uses `FileSystemStorage`. Uploaded files are written to the `media/` directory at the project root.

Django serves these files directly when `DEBUG=True` via the URL prefix `/media/`. The `docker-compose.yml` mounts a Docker volume `media_data` at the container path so files persist across restarts.

**Development storage path:** `media/listings/`, `media/merchants/`, `media/charities/`
**Development media URL:** `http://localhost:8000/media/<path>`

This approach is simple but not suitable for production because:

- It does not scale across multiple server instances.
- It is not backed up automatically.
- Static file serving by Django/Gunicorn is slow compared to a CDN.

### Development: MinIO (S3-compatible)

The `docker-compose.yml` includes a `minio` service that provides an S3-compatible API running locally on port `9000`. The MinIO browser console runs on port `9001`.

To use MinIO in development (instead of plain local storage), set `USE_S3=True` in your `.env` and keep `AWS_S3_ENDPOINT_URL=http://localhost:9000` pointing to the local MinIO service. This is useful for testing the full S3 code path before deploying to real AWS.

MinIO console login: `http://localhost:9001` with credentials `minioadmin` / `minioadmin` (from `.env.example`).

### Production: AWS S3

When `USE_S3=True` and `AWS_S3_ENDPOINT_URL` is empty, Django writes to real AWS S3 via `django-storages` (`S3Boto3Storage`).

**Production storage setup:**

1. Create an S3 bucket in your AWS account (e.g., `savefood-media-prod`).
2. Create an IAM user with `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` permissions scoped to that bucket.
3. Set `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from the IAM user credentials.
4. Set `AWS_STORAGE_BUCKET_NAME=savefood-media-prod`.
5. Set `AWS_S3_REGION_NAME` to your bucket's region (e.g., `eu-west-3` for Paris).
6. Optionally, set `AWS_S3_CUSTOM_DOMAIN` to a CloudFront distribution domain for CDN delivery.

**Bucket CORS configuration** must allow the mobile app and admin dashboard to make direct reads from the bucket URL.

### File Upload Flow

```
Flutter App
  │  uploads multipart/form-data to /api/v1/listings/{id}/images/
  ▼
Django REST API
  │  validates MIME type, size, and dimensions via Pillow + python-magic
  │  resizes image if needed (thumbnail + full size)
  ▼
MinIO (dev) or S3 (prod)
  │  stores file, returns URL
  ▼
Django saves URL in Listing.images FK
  ▼
Flutter App
  │  subsequent GET /api/v1/listings/{id}/ returns image URLs
  │  loads images directly from MinIO/S3/CDN URL
```

The API **never sends image binary data in API responses** — it sends URLs. The mobile app fetches image bytes directly from the storage URL.

---

## 6. Running the Backend Locally

### Prerequisites

| Tool           | Version                          | Notes                                    |
| -------------- | -------------------------------- | ---------------------------------------- |
| Docker Desktop | 4.x+                             | Required for the Docker-based approach   |
| Docker Compose | V2 (bundled with Docker Desktop) | Use `docker compose` (space, not hyphen) |
| Python         | 3.11+                            | Required only for non-Docker setup       |
| Poetry         | 1.8+                             | Required only for non-Docker setup       |
| Git            | Any                              | For cloning                              |

### Method A — Docker Compose (Recommended)

This is the simplest approach. All infrastructure (Postgres, Redis, MinIO) is started automatically.

**Step 1 — Clone and enter the backend directory**

```bash
cd backend/
```

**Step 2 — Create your environment file**

```bash
cp .env.example .env
```

The defaults in `.env.example` are pre-configured to work with the Docker Compose services. You do not need to change anything to run locally.

**Step 3 — Start all services**

```bash
docker compose up --build
```

This builds the Django image, starts PostgreSQL, Redis, and MinIO, waits for each to be healthy, then starts the Django development server.

On first run, the `web` service automatically runs `python manage.py migrate` before starting `runserver`.

**Step 4 — Create the superuser (first time only)**
In a second terminal, while the containers are running:

```bash
docker compose exec web python manage.py createsuperuser
```

You will be prompted for an email and password. This account is used to access `/admin/`.

**Step 5 — (Optional) Load seed data**

```bash
docker compose exec web python manage.py runscript seed_data
```

This populates the database with sample merchants, listings, and users for development and testing.

**Step 6 — Verify everything is running**

| URL                               | What to expect                |
| --------------------------------- | ----------------------------- |
| `http://localhost:8000/health/`   | `{"status": "ok"}`            |
| `http://localhost:8000/admin/`    | Django Admin login page       |
| `http://localhost:8000/api/docs/` | Swagger UI with all endpoints |
| `http://localhost:9001/`          | MinIO browser console         |
| `http://localhost:5555/`          | Flower — Celery task monitor  |

**Stopping:**

```bash
docker compose down
```

Add `-v` to also delete the named volumes (database data, Redis data, uploaded files):

```bash
docker compose down -v
```

---

### Method B — Manual (Without Docker)

Use this if Docker is unavailable or if you need to run services on your host machine.

**Step 1 — Install system dependencies**

On Ubuntu/Debian:

```bash
sudo apt-get install -y \
    python3.11 python3.11-dev \
    postgresql-15 postgresql-15-postgis-3 \
    redis-server \
    libgdal-dev gdal-bin \
    libpq-dev \
    libmagic-dev
```

On macOS (Homebrew):

```bash
brew install python@3.11 postgresql@15 postgis redis libmagic gdal
```

**Step 2 — Install Poetry and project dependencies**

```bash
pip install poetry
cd backend/
poetry install
```

**Step 3 — Configure PostgreSQL and create the database**

Start the PostgreSQL service, then:

```bash
psql -U postgres -c "CREATE USER savefood_user WITH PASSWORD 'savefood_pass';"
psql -U postgres -c "CREATE DATABASE savefood_db OWNER savefood_user;"
psql -U postgres -d savefood_db -c "CREATE EXTENSION postgis;"
```

**Step 4 — Configure environment variables**

```bash
cp .env.example .env
```

Edit `.env` if needed to match your local PostgreSQL and Redis connection strings.

**Step 5 — Run database migrations**

```bash
poetry run python manage.py migrate
```

**Step 6 — Create superuser**

```bash
poetry run python manage.py createsuperuser
```

**Step 7 — Start Redis (in a separate terminal)**

```bash
redis-server
```

**Step 8 — Start Celery worker (in a separate terminal)**

```bash
poetry run celery -A config.celery worker -l info -Q default,notifications,analytics -c 4
```

**Step 9 — Start Celery Beat scheduler (in another terminal)**

```bash
poetry run celery -A config.celery beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

**Step 10 — Start the Django development server**

```bash
poetry run python manage.py runserver 0.0.0.0:8000
```

The API will be available at `http://localhost:8000/api/v1/`.

---

### Environment: Development vs Production

| Behaviour      | Development                 | Production                          |
| -------------- | --------------------------- | ----------------------------------- |
| `DEBUG`        | `True`                      | `False`                             |
| Error pages    | Detailed Django debug pages | Generic JSON error responses        |
| Email delivery | Printed to terminal console | Sent via SMTP (SendGrid or similar) |
| File storage   | Local disk or MinIO         | AWS S3                              |
| CORS           | All origins allowed         | Only `CORS_ALLOWED_ORIGINS` list    |
| Password rules | None enforced               | Full validators active              |
| HTTPS          | Not required                | Enforced (redirects HTTP → HTTPS)   |
| Cache backend  | Django local memory cache   | Redis                               |
| Web server     | Django `runserver`          | Gunicorn behind Nginx               |

---

## 7. Connecting the Flutter Mobile App

### Base API URL

The Flutter app needs a configurable base URL that points to the running API.

| Environment                                | Base URL                         |
| ------------------------------------------ | -------------------------------- |
| Local development (device on same network) | `http://192.168.x.x:8000/api/v1` |
| Local development (Android emulator)       | `http://10.0.2.2:8000/api/v1`    |
| Local development (iOS simulator)          | `http://127.0.0.1:8000/api/v1`   |
| Production                                 | `https://api.savefood.dz/api/v1` |

Define this as a constant or environment configuration in the Flutter app so it can be switched without modifying business logic.

**Android emulator note:** The Android emulator runs in a virtual machine and cannot reach `localhost` on the host machine. Use the special alias `10.0.2.2` which the emulator maps to the host's loopback interface.

### Authentication Flow (JWT)

The SaveFood DZ API uses **JWT (JSON Web Tokens)** for mobile authentication. There are two tokens:

- **Access token**: Short-lived (60 minutes). Sent with every API request.
- **Refresh token**: Long-lived (30 days). Used only to get a new access token when the current one expires.

**Full flow:**

```
1. User registers or logs in
   POST /api/v1/auth/login/
   Body: { "email": "...", "password": "..." }
   Response: { "access": "eyJ...", "refresh": "eyJ..." }

2. Store both tokens securely
   - Never store in plain SharedPreferences
   - Use flutter_secure_storage for production

3. Send the access token with every API request
   Header: Authorization: Bearer eyJ...

4. When the API returns 401 Unauthorized:
   - The access token has expired
   - Automatically call /api/v1/auth/token/refresh/
   - Body: { "refresh": "<stored refresh token>" }
   - Response: { "access": "<new access token>" }
   - Retry the original failed request with the new token

5. When the user logs out:
   POST /api/v1/auth/logout/
   Body: { "refresh": "<refresh token>" }
   This blacklists the refresh token server-side, preventing reuse.
   Then delete both tokens from secure storage.
```

### Request/Response Format

**Request headers required on all authenticated calls:**

```
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
```

For file uploads (multipart/form-data):

```
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```

**Standard success response structure:**

```json
{
  "id": "uuid",
  "field": "value",
  ...
}
```

For lists, the API uses **cursor-based pagination**:

```json
{
  "next": "http://api.savefood.dz/api/v1/listings/?cursor=...",
  "previous": null,
  "results": [ ... ]
}
```

**Standard error response structure:**

```json
{
  "detail": "Human-readable error message."
}
```

Or for field-level validation errors:

```json
{
  "email": ["This field is required."],
  "password": ["This password is too short."]
}
```

### HTTP Status Codes Used

| Code                        | Meaning                  | Flutter action                       |
| --------------------------- | ------------------------ | ------------------------------------ |
| `200 OK`                    | Success                  | Parse response body                  |
| `201 Created`               | Resource created         | Parse response body                  |
| `204 No Content`            | Success, no body         | Confirm operation succeeded          |
| `400 Bad Request`           | Validation error         | Show field-level error messages      |
| `401 Unauthorized`          | Token expired or invalid | Trigger token refresh flow           |
| `403 Forbidden`             | Insufficient permissions | Show access denied message           |
| `404 Not Found`             | Resource does not exist  | Show not found message               |
| `429 Too Many Requests`     | Rate limit exceeded      | Show "try again later" and backoff   |
| `500 Internal Server Error` | Server bug               | Show generic error, log to analytics |

### Environment Switching in Flutter

Define a configuration class that reads from compile-time environment variables or a config file:

```dart
// Define in a constants or config file
abstract final class ApiConfig {
  static const String baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://10.0.2.2:8000/api/v1',
  );
}
```

To build with production URL:

```bash
flutter run --dart-define=API_BASE_URL=https://api.savefood.dz/api/v1
```

This allows switching environments at build time without changing code.

### Recommended Flutter Architecture for API Layer

```
lib/core/api/
  api_client.dart        ← Dio/http instance with base URL, headers, interceptors
  auth_interceptor.dart  ← Adds Bearer token to every request, handles 401 → refresh
  api_exception.dart     ← Maps HTTP errors to typed exceptions
  endpoints.dart         ← All endpoint path constants

lib/core/services/
  auth_service.dart      ← login(), logout(), refreshToken(), isLoggedIn()
  storage_service.dart   ← Secure storage wrapper for token persistence
```

Each feature module then calls its own repository, which calls `api_client.dart`.

---

## 8. Connecting the Admin Dashboard

### Overview

The SaveFood DZ admin interface has two layers:

1. **Django Admin** — The built-in, browser-rendered admin panel at `/admin/`. Available immediately. Used for direct data management, user moderation, and system oversight.

2. **Custom Admin API** — REST endpoints under `/api/v1/analytics/admin/` for a future custom frontend dashboard. Protected by `IsAdminUser` permission.

### Django Admin Access

| Detail         | Value                                                                          |
| -------------- | ------------------------------------------------------------------------------ |
| URL            | `http://localhost:8000/admin/` (dev) / `https://api.savefood.dz/admin/` (prod) |
| Authentication | Session-based (username + password form login, **not** JWT)                    |
| Required role  | Staff (`is_staff=True`) or Superuser (`is_superuser=True`)                     |

To create the first admin account: `python manage.py createsuperuser`

To promote an existing user to staff via API or shell:

```python
user = User.objects.get(email="admin@savefood.dz")
user.is_staff = True
user.save()
```

### Django Admin Capabilities (by app)

| Module        | What admin staff can do                                               |
| ------------- | --------------------------------------------------------------------- |
| Users         | View all accounts, activate/deactivate, change roles, reset passwords |
| Merchants     | Approve pending merchant applications, view merchant profiles         |
| Charities     | Approve charity registrations, verify documents                       |
| Listings      | View, moderate, or remove any listing                                 |
| Orders        | View all orders, resolve disputes                                     |
| Donations     | View donation activity and charity claims                             |
| Reviews       | Moderate or remove inappropriate reviews                              |
| Notifications | Send platform-wide announcements                                      |
| Analytics     | View all merchant and platform stats                                  |
| Celery Beat   | Schedule or modify periodic Celery tasks                              |

### Admin User Roles

| Role      | `is_staff` | `is_superuser` | Access                        |
| --------- | ---------- | -------------- | ----------------------------- |
| Consumer  | `False`    | `False`        | Mobile app only               |
| Merchant  | `False`    | `False`        | Mobile app only               |
| Charity   | `False`    | `False`        | Mobile app only               |
| Moderator | `True`     | `False`        | Django Admin (limited)        |
| Superuser | `True`     | `True`         | Django Admin (full) + all API |

Superusers have unrestricted access. Moderators can access models that their group permissions allow. Group permissions are configured in the Django Admin under **Authentication → Groups**.

### Custom Admin REST Endpoints

For a custom web dashboard (e.g., a separate React/Vue frontend), the following REST endpoints are available and protected by admin-only permissions:

| Endpoint                                 | Description                                                    |
| ---------------------------------------- | -------------------------------------------------------------- |
| `GET /api/v1/analytics/admin/`           | Platform-wide KPIs: total users, total orders, total donations |
| `GET /api/v1/analytics/admin/merchants/` | Per-merchant performance stats                                 |
| `GET /api/v1/analytics/admin/listings/`  | Listing activity metrics                                       |
| `GET /api/v1/analytics/admin/impact/`    | Environmental impact totals                                    |

These endpoints require a **JWT access token** from an account with `is_staff=True`. The custom dashboard authenticates the same way as the mobile app — via POST to `/api/v1/auth/login/` — but the user must be a staff account.

### CORS for the Admin Dashboard

If the admin dashboard runs on a separate web origin (e.g., `http://admin.savefood.dz`), add that origin to the `CORS_ALLOWED_ORIGINS` environment variable:

```
CORS_ALLOWED_ORIGINS=http://localhost:3000,https://admin.savefood.dz
```

Mobile apps do not have a browser origin, so they are not subject to CORS.

---

## 9. Development Best Practices

### Project Structure

- **One concern per app.** Each of the eight apps owns its models, serializers, views, URLs, and business logic. Never reach across app boundaries at the model layer — use service classes for cross-app coordination.
- **Keep views thin.** Views should only handle HTTP concerns: parse the request, call a service function, serialize the result, return the response. Business logic lives in `services.py`, not in views.
- **Use `services.py` for transactions.** Any operation that modifies more than one model should be wrapped in a `django.db.transaction.atomic()` block inside a service function.
- **Signal discipline.** `signals.py` is reserved for lightweight, cross-cutting concerns (e.g., creating a notification when an order is confirmed). Never trigger Celery tasks or send emails directly inside signals — dispatch a Celery task instead to keep request cycles fast.

### Security Practices

- **Never commit secrets.** The `.gitignore` already excludes `.env`. Always use `.env.example` (with fake/placeholder values) as the committed reference. Rotate `SECRET_KEY` and all API credentials if they are ever exposed.
- **Principle of least privilege on file uploads.** Validate `Content-Type` with `python-magic` (not just file extension). Set max file size at the nginx and Django level. Resize images on upload to prevent storing malicious oversized files.
- **JWT token hygiene.** Keep access token lifetime short (60 minutes). Enforce refresh token rotation and blacklisting so stolen refresh tokens cannot be reused indefinitely.
- **Input validation.** Use DRF serializers with explicit field types, validators, and `read_only_fields` for all API inputs. Never pass `request.data` directly to a model constructor.
- **Rate limiting.** The `AUTH_RATELIMIT` (5 attempts per 15 minutes) on login/register endpoints is critical — do not disable in production.
- **SQL injection prevention.** Always use Django ORM query methods. Never interpolate user input into raw SQL strings. If raw queries are absolutely necessary, use parameterized `cursor.execute(sql, params)`.

### Database Optimization

- **Index strategically.** Every field used in `.filter()`, `.order_by()`, or `.annotate()` calls should have a database index. Spatial fields (`PointField`) require PostGIS `GistIndex`, not the default `BTreeIndex`.
- **Select related data eagerly.** Use `.select_related()` for ForeignKey joins and `.prefetch_related()` for ManyToMany or reverse FK relations in list views to eliminate N+1 query problems.
- **Use `CONN_MAX_AGE`.** The settings already configure `CONN_MAX_AGE=60` to reuse database connections across requests. Do not set this to `None` (unlimited) in production as it can exhaust the database connection pool under load.
- **Defer expensive fields.** For list views that return many results, use `.defer('large_text_field')` or `.only('id', 'title', ...)` to avoid loading unused columns.
- **Never paginate with OFFSET at scale.** The API uses **cursor-based pagination** for mobile endpoints. Do not switch to offset-based pagination for large tables — it becomes prohibitively slow as the page number grows.

### Logging

- **Structured JSON logs in production.** The logging configuration uses `python-json-logger` to write machine-parseable JSON to `logs/django.log`. This makes logs searchable in tools like Datadog, Loki, or CloudWatch without custom parsers.
- **Log at the right level.** Use `DEBUG` for query-level diagnostics, `INFO` for normal application events (user registered, order created), `WARNING` for unexpected-but-recoverable situations, `ERROR` for exceptions that need investigation.
- **Include request IDs.** The `RequestIDMiddleware` attaches a `X-Request-ID` header to every request and adds it to the logging context. Always include this ID when reporting API errors to make trace correlation possible.
- **Never log sensitive data.** Do not log passwords, tokens, credit card numbers, or full request bodies containing PII.

### Error Handling

- **Custom exception handler.** The project uses `apps.core.exceptions.custom_exception_handler` (configured in `REST_FRAMEWORK`). All exceptions — including Django's built-in `ValidationError`, `PermissionDenied`, `NotFound` — are normalized to a consistent JSON structure before being returned to clients.
- **Use typed exceptions.** Define domain-specific exceptions in `apps.core.exceptions` (e.g., `ListingNotAvailableError`, `OrderAlreadyCompletedError`) and raise them from service functions. The exception handler maps them to the appropriate HTTP status codes.
- **Celery task failure handling.** All Celery tasks must have `autoretry_for=(Exception,)` with `max_retries=3` and exponential backoff. Log failures and send them to Sentry. Never let a task silently fail.

### Scalability

- **Stateless web workers.** The Django application is stateless — no in-process state between requests. This means multiple Gunicorn workers or multiple container replicas can run in parallel without coordination. The `docker-compose.prod.yml` already defines `replicas: 2` for the web service.
- **Heavy work in Celery.** Any operation taking more than ~200ms — sending emails, generating QR codes, computing analytics aggregates, sending SMS — must be offloaded to a Celery task. Keeping API response times under 500ms requires this discipline.
- **Cache aggressively but correctly.** Cache paginated listing results (short TTL, 60–120 seconds) and merchant stats (medium TTL, 300 seconds). Use cache invalidation signals when data changes so that stale data is not served after updates.
- **Use read replicas for analytics.** When the platform grows, analytics queries (aggregating thousands of orders over date ranges) should run against a PostgreSQL read replica, not the primary. Point `services.py` analytics queries to `using("analytics")` when a read replica is configured.
- **Monitor Celery queue depth.** Use Flower (available at `:5555` in development) to watch queue lengths. If the `notifications` queue grows faster than workers consume it, scale up `celery_worker` replicas before users notice delayed notifications.

---

_Document version: 1.0 — aligned with backend tag after initial scaffold. Update when architecture decisions change._
