FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    wget \
    curl \
    ca-certificates \
    tesseract-ocr \
    tesseract-ocr-spa \
    tesseract-ocr-cat \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala navegadores y dependencias del sistema para Playwright.
# La opción --with-deps es la recomendada por la documentación oficial.
RUN python -m playwright install --with-deps chromium

COPY . .

RUN chmod +x /app/start.sh \
    && chmod +x /app/audit.sh \
    && chmod +x /app/audits/visual/run.sh

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app \
    && mkdir -p /app/media/audit-reports /app/audits/visual/reports /app/audits/visual/screenshots /ms-playwright \
    && chown -R app:app /app /ms-playwright

USER app

EXPOSE 8000

CMD ["bash", "/app/start.sh"]
