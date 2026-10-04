FROM python:3.11-slim
WORKDIR /db
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
USER 1000
CMD ["python", "load_data.py"]
