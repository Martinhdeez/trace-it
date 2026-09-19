FROM python:3.12-slim-bookworm
WORKDIR /srv
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY --chmod=0444 alberto_erp.py server.py ./
USER 10001:10001
CMD ["python", "server.py"]
