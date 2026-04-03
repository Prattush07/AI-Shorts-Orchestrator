@echo off
echo ==========================================
echo Starting AI Shorts Orchestrator...
echo ==========================================

:: Start Backend in a new window
start "FastAPI Backend" cmd /c "call start_backend.bat"

:: Start Frontend in a new window
echo Starting Frontend...
cd frontend
npm run dev

pause
