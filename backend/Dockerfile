FROM python:3.11-slim

# Instalar dependencias de Chromium manualmente (Debian Trixie compatible)
# NO usamos playwright install-deps porque intenta instalar ttf-unifont que no existe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 \
    libgbm1 libasound2t64 libxss1 libxtst6 libxrandr2 \
    fonts-liberation libpango-1.0-0 libcairo2 libcups2 \
    libdbus-1-3 libxdamage1 libxfixes3 libxcomposite1 \
    libatk1.0-0 libglib2.0-0 libx11-6 libxcb1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Solo instalar el browser, sin install-deps (ya instalamos manualmente arriba)
RUN playwright install chromium

COPY . .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "300", "app:app"]

