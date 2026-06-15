# Tawfir Notification Setup Notes

## Current State

- The backend already has `apps.notifications` with `Notification`, `NotificationPreference`, API endpoints, admin registration, and Celery tasks.
- The current backend supports in-app, email, SMS, and a `push` channel, but `apps.notifications.backends.fcm.FCMBackend` is still a stub.
- There is no `firebase_admin` dependency installed yet.
- There is no Firebase service account JSON in the backend repo.
- The Flutter app already has an in-app notifications feature wired to `/api/v1/notifications/`.
- The Flutter app does not yet include `firebase_messaging` or `flutter_local_notifications`, so device push tokens are not registered with the backend.

## Existing API Shape

The current Flutter app matches these backend endpoints:

- `GET /api/v1/notifications/`
- `GET /api/v1/notifications/unread-count/`
- `POST /api/v1/notifications/mark-read/` with `{ "notification_ids": ["..."] }`
- `POST /api/v1/notifications/mark-all-read/`
- `GET/PUT /api/v1/notifications/preferences/`

Do not replace these endpoints with a new shape unless the Flutter app is migrated at the same time.

## Local Test Prerequisites

Start the backend dependencies before testing notifications:

```powershell
docker compose up -d db redis
```

If Docker Desktop is not running, start it first. The local Django settings expect PostgreSQL/PostGIS on `localhost:5432`.

## Manual In-App Notification Test

After the database is running:

```powershell
poetry run python manage.py migrate
poetry run python manage.py send_notification --user-id <USER_UUID> --type system --title "Test" --body "This is a Tawfir notification test"
```

For all active users:

```powershell
poetry run python manage.py send_notification --all-users --type system --title "Test" --body "This is a Tawfir notification test"
```

Then open the app notification inbox or call:

```powershell
curl -H "Authorization: Bearer <TOKEN>" http://localhost:8080/api/v1/notifications/
```

## Real Push Notification Requirements

To test real push notifications on a device, add these in a separate focused change:

- Backend: add `firebase-admin`, an `FCMDevice` model/table, device registration endpoints, and replace the FCM stub with Firebase Admin SDK sending.
- Backend: add Firebase service account JSON outside version control, for example `firebase-service-account.json`, and load it from settings.
- Flutter: add `firebase_messaging` and `flutter_local_notifications`.
- Flutter: request notification permission, get the FCM token, and register it with the backend.
- Platform: confirm Android notification channel metadata and iOS APNs/Firebase configuration.

The generated prompt is useful as a checklist, but it does not match this repo exactly. Apply it in small migrations instead of as one large rewrite.
