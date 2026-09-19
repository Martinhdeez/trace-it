FROM node:24-bookworm-slim AS build
WORKDIR /src
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
ENV VITE_API_MODE=live VITE_API_URL=/nexia/trace-it/api
RUN npm run lint && npm run build -- --base=/nexia/trace-it/

FROM nginxinc/nginx-unprivileged:1.28-alpine
ARG REVISION=local
LABEL org.opencontainers.image.source="https://github.com/Martinhdeez/trace-it" \
      org.opencontainers.image.revision=$REVISION
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html/nexia/trace-it
