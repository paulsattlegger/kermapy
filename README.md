# kermapy

Kerma protocol node in Python

## How to use

Via `docker-compose.yml`

```yaml
version: "3"
services:
  chain-node:
    image: ghcr.io/paulsattlegger/kermapy:v1.0.5
    environment:
      BOOTSTRAP_NODES: "128.130.122.101:18018"
      LISTEN_ADDR: "0.0.0.0:18018"
      STORAGE_PATH: "/app/data/peers.json"
      CLIENT_CONNECTIONS: 8
    stop_signal: SIGINT
    volumes:
      - "./data:/app/data"
    restart: unless-stopped
    ports:
      - "18018:18018"
```

Via `systemd`

```bash
sudo useradd --system --shell /sbin/nologin kermapy
sudo mkdir --parents /opt/kermapy
sudo python -m venv /opt/kermapy/venv
sudo chown --recursive kermapy:kermapy /opt/kermapy
/opt/kermapy/venv/bin/pip install -r /opt/kermapy/requirements.txt
```

```ini
[Unit]
Description=Kerma protocol node in Python
[Service]
User=kermapy
Group=kermapy
KillSignal=SIGINT
WorkingDirectory=/opt/kermapy/src/kermapy/
ExecStart=/opt/kermapy/venv/bin/python3 kermapy.py
[Install]
WantedBy=multi-user.target
```
