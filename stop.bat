@echo off
echo ========================================================
echo   Stopping PSF - Post Service Follow-up Stack
echo ========================================================
echo.

echo [INFO] Shutting down PSF containers (preserving volumes)...
docker compose down

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [OK] All PSF containers have been stopped safely.
) else (
    echo.
    echo [WARNING] Encountered an issue stopping containers.
)

echo.
pause

