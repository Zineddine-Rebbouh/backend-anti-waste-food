@echo off
echo ===================================================
echo SaveFood DZ - Test Environment Setup
echo ===================================================

echo [1/4] Starting Database and Redis...
docker-compose up -d db redis

echo [2/4] Waiting for Database to be ready...
:check_db
docker-compose exec db pg_isready -U savefood_user -d savefood_db >nul 2>&1
if %errorlevel% neq 0 (
    timeout /t 2 >nul
    goto check_db
)
echo Database is ready!

echo [3/4] Applying Migrations...
docker-compose run --rm web python manage.py migrate

echo [4/4] Seeding Algerian Market Data...
docker-compose run --rm web python manage.py seed_algeria --clear

echo ===================================================
echo Setup Complete!
echo You can now start the application with:
echo docker-compose up
echo ===================================================
pause
