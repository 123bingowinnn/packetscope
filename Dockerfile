FROM python:3.12-slim

# System packages required for the real PacketScope measurements:
#   - iputils-ping  → /bin/ping for ICMP RTT and packet loss
#   - traceroute    → /usr/sbin/traceroute for hop-by-hop route discovery
#   - ca-certificates → so the Python ssl module trusts public CAs
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        iputils-ping \
        traceroute \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY packetscope ./packetscope
COPY web ./web

ENV PYTHONUNBUFFERED=1 \
    PORT=8000

EXPOSE 8000

CMD ["sh", "-c", "python3 -m packetscope web --host 0.0.0.0 --port ${PORT}"]
