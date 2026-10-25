FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --uid 10001 --create-home life
COPY . .
USER life
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "life.api:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
