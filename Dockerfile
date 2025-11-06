FROM python:3.11.5-alpine
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/__init__.py .
COPY app/auth.py .
COPY app/config.py .
COPY app/crud.py .
COPY app/database.py .
COPY app/main.py .
COPY app/models.py .
COPY app/schemas.py .
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8888"]