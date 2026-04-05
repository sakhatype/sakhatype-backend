FROM python:3.13-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# На случай, если StaticFiles проверит каталог до первого запроса; основное создание — в main.py + lifespan.
RUN mkdir -p /app/uploads/avatars

ENV PORT=80
EXPOSE 80

CMD ["python", "main.py"]
