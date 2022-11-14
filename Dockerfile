FROM python:3.11-bullseye as builder

ENV PIP_DISABLE_PIP_VERSION_CHECK 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y g++ libleveldb-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11.0-slim

RUN apt-get update && \
    apt-get install -y libleveldb1d

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY src/kermapy .

CMD [ "python", "/app/kermapy.py" ]