FROM python:3.12-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
RUN addgroup --system app && adduser --system --group app && \
    pip install --no-cache-dir gunicorn
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .
USER app
EXPOSE 7860
ENV FLASK_ENV=production \
    PORT=7860 \
    HOST=0.0.0.0 \
    LOG_LEVEL=INFO
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:7860", "--timeout", "300", "--access-logfile", "-", "--error-logfile", "-", "webapp:app"]
