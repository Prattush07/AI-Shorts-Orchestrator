cd backend
call venv\Scripts\activate
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --reload
