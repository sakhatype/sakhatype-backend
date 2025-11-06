FROM python:3.11.5-alpine
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/__init__.py ./app/
COPY app/auth.py ./app/
COPY app/config.py ./app/
COPY app/crud.py ./app/
COPY app/database.py ./app/
COPY app/main.py ./app/
COPY app/models.py ./app/
COPY app/schemas.py ./app/
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8888"]