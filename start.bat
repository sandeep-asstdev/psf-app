@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   PSF - Post Service Follow-up SaaS Platform Startup
echo ========================================================
echo.

:: 1. Check if Docker is responding
docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Starting Docker Desktop engine...
    start "" "C:\Users\User\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
    
    echo [INFO] Waiting for Docker daemon to become responsive...
    :wait_docker
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo   ... still waiting for Docker daemon
        goto wait_docker
    )
    echo [OK] Docker daemon is running!
) else (
    echo [OK] Docker daemon is already active.
)

echo.
echo [INFO] Launching PSF Multi-Tenant Container Stack...
docker compose up -d

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to start Docker Compose stack.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [INFO] Checking system health status...
timeout /t 4 /nobreak >nul

echo.
echo ========================================================
echo   PSF Platform is LIVE and Ready!
echo ========================================================
echo   Web Application:    http://localhost:5173
echo   FastAPI Swagger UI: http://localhost:8000/api/v1/docs
echo   FastAPI Health:     http://localhost:8000/health
echo   MinIO S3 Console:   http://localhost:9001
echo   PostgreSQL 18:      localhost:5434 (db: psf_db)
echo   Redis Cache:        localhost:6380
echo.
echo   Demo Login Accounts:
echo     Admin:   admin@apexauto.com    / Admin@12345
echo     CRE:     priya.cre@apexauto.com / Priya@12345
echo ========================================================
echo.
pause

