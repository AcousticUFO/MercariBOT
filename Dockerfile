FROM python:3.12-slim

# Prevent bytecode generation and ensure unbuffered logging output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Create unprivileged dedicated service user (OWASP Container Hardening)
RUN groupadd -g 10001 mercaribot && \
    useradd -u 10001 -g mercaribot -m -s /bin/sh mercaribot

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Install package in editable mode and grant ownership to service user
RUN pip install --no-cache-dir -e . && \
    chown -R mercaribot:mercaribot /app

# Run as non-root user
USER 10001:10001

CMD ["python", "main.py"]
