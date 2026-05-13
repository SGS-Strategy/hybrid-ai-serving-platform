FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY operation_simulator.py .

CMD ["python", "operation_simulator.py"]