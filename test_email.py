"""
Temporary script to test email configuration.
Run with: poetry run python test_email.py
"""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
django.setup()

from django.conf import settings
from django.core.mail import send_mail

print("=" * 50)
print("EMAIL SETTINGS CHECK")
print("=" * 50)
print(f"EMAIL_BACKEND    : {settings.EMAIL_BACKEND}")
print(f"EMAIL_HOST       : {settings.EMAIL_HOST}")
print(f"EMAIL_PORT       : {settings.EMAIL_PORT}")
print(f"EMAIL_USE_TLS    : {settings.EMAIL_USE_TLS}")
print(f"EMAIL_HOST_USER  : {settings.EMAIL_HOST_USER}")
print(f"EMAIL_HOST_PASS  : {'***SET***' if settings.EMAIL_HOST_PASSWORD else 'EMPTY - NOT SET!'}")
print(f"DEFAULT_FROM     : {settings.DEFAULT_FROM_EMAIL}")
print()

if not settings.EMAIL_HOST_USER:
    print("ERROR: EMAIL_HOST_USER is empty. Check your .env file.")
    exit(1)

if not settings.EMAIL_HOST_PASSWORD:
    print("ERROR: EMAIL_HOST_PASSWORD is empty. Check your .env file.")
    exit(1)

# Also check Redis (needed for OTP token storage)
print("=" * 50)
print("REDIS CACHE CHECK")
print("=" * 50)
try:
    from django.core.cache import cache
    cache.set("savefood_test_key", "ok", timeout=10)
    result = cache.get("savefood_test_key")
    if result == "ok":
        print("Redis cache: OK")
    else:
        print("Redis cache: FAILED (set/get mismatch)")
except Exception as e:
    print(f"Redis cache: FAILED — {e}")
    print("TIP: Run 'docker-compose up -d redis' to start Redis.")

print()
print("=" * 50)
print("SENDING TEST EMAIL")
print("=" * 50)
recipient = "gougel777@gmail.com"  # send to yourself
print(f"Sending to: {recipient}")

try:
    send_mail(
        subject="SaveFood DZ — Email Test",
        message="This is a test email from your SaveFood DZ backend. Email is working correctly!",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient],
        fail_silently=False,
    )
    print("SUCCESS! Email sent. Check your inbox.")
except Exception as e:
    print(f"FAILED: {e}")
    print()
    if "Authentication" in str(e) or "Username" in str(e) or "535" in str(e):
        print("HINT: Gmail requires an App Password (not your real password).")
        print("  1. Enable 2-Step Verification at myaccount.google.com/security")
        print("  2. Go to myaccount.google.com/apppasswords")
        print("  3. Create a new App Password")
        print("  4. Update EMAIL_HOST_PASSWORD in your .env file with the 16-digit code")
    elif "Connection" in str(e) or "refused" in str(e):
        print("HINT: Cannot connect to Gmail SMTP. Check your internet connection.")
