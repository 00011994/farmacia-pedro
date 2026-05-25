FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN python scripts/seed_demo_db.py

CMD ["python", "scripts/run_demo.py"]
