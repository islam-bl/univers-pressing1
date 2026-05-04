web: python -c "from models.database import init_db; init_db()" && gunicorn app:app --bind 0.0.0.0:$PORT
