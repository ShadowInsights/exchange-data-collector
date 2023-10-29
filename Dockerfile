# Use an official lightweight Python image.
# https://hub.docker.com/_/python
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies and poetry
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev build-essential \
    && pip install --upgrade pip \
    && pip install poetry

# Set the working directory
WORKDIR /app

# Copy only requirements to cache them in docker layer
COPY pyproject.toml poetry.lock /app/

# Project initialization:
RUN poetry config virtualenvs.create false \
    && poetry install --only main

# -----

# Production Image
FROM python:3.12-slim as production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONPATH=/home/app

# Create directory for the app user
RUN mkdir -p /home/app

# Create the app user
RUN addgroup --system app && adduser --system --group app

# Create the appropriate directories
WORKDIR /home/app

# Copy the content from the builder stage
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app /app
COPY ./app /home/app/app

# Change to a non-root user
USER app

EXPOSE 8080

# Command to run the application
CMD ["python", "./app/main.py"]