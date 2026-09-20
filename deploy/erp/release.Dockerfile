FROM python:3.12-slim-bookworm
ARG SOURCE_HASH
LABEL org.trace-it.source-hash=$SOURCE_HASH
ARG REVISION
LABEL org.opencontainers.image.revision=$REVISION
LABEL org.opencontainers.image.source="https://github.com/Martinhdeez/trace-it"
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
# release.py creates this context exclusively from checksum-verified public files.
COPY . ./
RUN chmod -R a=rX /srv
USER 10001:10001
CMD ["python", "server.py"]
