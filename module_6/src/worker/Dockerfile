FROM python:3.11-slim
WORKDIR /worker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8080
USER 1000
ENV PYTHONUNBUFFERED=1
CMD ["python", "consumer.py"]
