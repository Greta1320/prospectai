FROM python:3.11-slim

# Dependencias del sistema para Playwright/Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2 libxss1 libxtst6 \
    fonts-liberation libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instalar Chromium para Playwright
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "300", "app:app"]
