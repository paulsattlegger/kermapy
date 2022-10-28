# kermapy
Kerma protocol node in Python

## How to use

Via `docker-compose.yml`

```yaml
version: "3"
services:
  chain-node:
    image: ghcr.io/paulsattlegger/kermapy:v1.0.1
    environment:
      BOOTSTRAP_NODES: "128.130.122.101:18018"
      LISTEN_ADDR: "0.0.0.0:18018"
      STORAGE_PATH: "/app/data/peers.json"
      CLIENT_CONNECTIONS: 8
    volumes:
      - "./data:/app/data"
    restart: unless-stopped
    ports:
      - 18018:18018
```