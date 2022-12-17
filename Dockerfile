FROM python:3.11 as builder

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS=yes
ARG PIP_DISABLE_PIP_VERSION_CHECK=1
ARG PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y libleveldb-dev

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
# --use-pep517: use PEP 517 for building source distributions (https://github.com/pypa/pip/issues/8559)
RUN pip install --use-pep517 -r requirements.txt

FROM python:3.11-slim

ARG DEBIAN_FRONTEND=noninteractive
ARG DEBCONF_NOWARNINGS=yes

COPY --from=builder /var/lib/apt/lists /var/lib/apt/lists

RUN apt-get install -y libleveldb1d && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY src/ .

CMD [ "python", "-m", "kermapy" ]