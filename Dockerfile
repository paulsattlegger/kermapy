FROM python:3.11.0-slim
WORKDIR /app

COPY requirements.txt ./
RUN pip install --requirement requirements.txt

COPY src/kermapy /app

CMD [ "python", "/app/kermapy.py" ]