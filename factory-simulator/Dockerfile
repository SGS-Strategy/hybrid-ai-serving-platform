FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY factory_simulator.py .

CMD ["python", "factory_simulator.py"]