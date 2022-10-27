FROM python:3.11.0-alpine
WORKDIR /app

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY src/kermapy /app

CMD [ "python", "/app/kermapy.py" ]