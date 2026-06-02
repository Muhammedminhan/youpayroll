FROM python:3.11.15-alpine3.22
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /youpayroll

# Install system dependencies
RUN apk add --no-cache \
    gcc \
    musl-dev \
    postgresql-dev \
    libjpeg-turbo-dev \
    zlib-dev \
    libffi-dev \
    netcat-openbsd

COPY requirements.txt /youpayroll/
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /youpayroll/
RUN chmod +x /youpayroll/entrypoint.sh

# Create a non-root user and set permissions (after COPY)
RUN addgroup -S appgroup && adduser -S appuser -G appgroup
RUN chown -R appuser:appgroup /youpayroll

USER appuser
ENTRYPOINT ["/youpayroll/entrypoint.sh"]
