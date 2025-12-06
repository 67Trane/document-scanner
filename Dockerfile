FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Collect static files at build time (optional)
# RUN python manage.py collectstatic --noinput

# Expose gunicorn on port 8000
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
