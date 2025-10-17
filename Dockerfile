FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/templates /app/static

COPY app/ /app/

EXPOSE 80

CMD ["python", "app.py"]