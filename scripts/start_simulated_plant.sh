#!/usr/bin/env bash
# Start the IPIS simulated plant stack.
#
# Brings up:
#   - Mosquitto MQTT broker
#   - InfluxDB historian
#   - Simulated OPC-UA server (replays benchmark data)
#   - FastAPI inference service
#   - Streamlit dashboard

set -euo pipefail

cd "$(dirname "$0")/.."

echo "============================================"
echo "  IPIS — Simulated plant stack startup"
echo "============================================"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "ERROR: docker not found. Install Docker first."
    exit 1
fi
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "ERROR: docker compose not found."
    exit 1
fi

# Bring up the stack
echo ""
echo ">>> Starting MQTT broker + InfluxDB + dashboard..."
docker compose -f docker/docker-compose.yml up -d

# Wait for broker
echo ""
echo ">>> Waiting for MQTT broker to be ready..."
sleep 3

# Start OPC-UA simulator in foreground
echo ""
echo ">>> Starting OPC-UA simulator (replays Debutanizer data)..."
echo "    Press Ctrl-C to stop."
echo ""
python -m ipis.module1_soft_sensor.serving.opcua_server \
    +dataset=debutanizer +deployment=level1
