FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r /app/requirements.txt

COPY src/ /app/src/

# Executa como usuario sem privilegios (boa pratica de seguranca)
RUN useradd --create-home --uid 10001 botuser && \
    mkdir -p /app/data /app/ticket_email_attachments && \
    chown -R botuser:botuser /app
USER botuser

CMD ["python", "src/bot.py"]
