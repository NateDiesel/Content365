FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app source code
COPY . .

# Remove any old Python cache files that might cause stale behavior
RUN find . -type d -name "__pycache__" -exec rm -r {} + \
    && find . -name "*.pyc" -delete

# Start the app
EXPOSE 8001
CMD sh -c 'uvicorn main:app --host 0.0.0.0 --port=${PORT:-8001}'
