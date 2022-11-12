FROM python:3.11.0-slim as builder

ENV PIP_DISABLE_PIP_VERSION_CHECK 1

WORKDIR /app

RUN apt-get update && \
    apt-get install --assume-yes --no-install-recommends g++ libleveldb-dev && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11.0-slim

RUN apt-get update && \
    apt-get install --assume-yes --no-install-recommends libleveldb1d && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY src/kermapy .

CMD [ "python", "/app/kermapy.py" ]