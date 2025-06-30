FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN find . -type d -name "__pycache__" -exec rm -r {} + \
    && find . -name "*.pyc" -delete

ENV PORT=8001

EXPOSE 8001
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
