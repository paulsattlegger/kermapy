FROM python:3.11 as builder

ENV PIP_DISABLE_PIP_VERSION_CHECK 1
ENV PIP_NO_CACHE_DIR 1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y g++ libleveldb-dev && \
    # remove state information for each package (unnecessary for docker image)
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# --use-pep517: use PEP 517 for building source distributions (https://github.com/pypa/pip/issues/8559)
RUN pip install --use-pep517 -r requirements.txt

FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y libleveldb1d && \
    # remove state information for each package (unnecessary for docker image)
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY src/kermapy .

CMD [ "python", "/app/kermapy.py" ]