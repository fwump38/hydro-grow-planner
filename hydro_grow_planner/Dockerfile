# Build from the repository root:  docker build -f hydro_grow_planner/Dockerfile .
# (The Supervisor can't build this itself, since it only sees the app folder, so CI
# publishes the image named in config.yaml.)

FROM node:22-alpine AS panel
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
# Vite writes the panel to ../backend/grow_planner/static
RUN npm run build

# The Supervisor no longer provides BUILD_FROM (2026.04+), so the base is named here.
# TODO: pin to a specific base image tag once the first release is built.
FROM ghcr.io/home-assistant/base:latest

RUN apk add --no-cache python3 py3-pip

WORKDIR /opt/grow_planner
COPY backend/requirements.txt ./
RUN python3 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir -r requirements.txt

COPY backend/grow_planner ./grow_planner
COPY --from=panel /build/backend/grow_planner/static ./grow_planner/static
COPY hydro_grow_planner/rootfs /
RUN chmod a+x /etc/services.d/grow-planner/run /etc/services.d/grow-planner/finish

LABEL io.hass.type="addon" \
      org.opencontainers.image.source="https://github.com/fwump38/hydro-grow-planner"
