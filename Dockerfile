FROM python:3.10.18-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo 'deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main' > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.lock .
RUN pip install --requirement requirements.lock
COPY backend backend
COPY frontend frontend
COPY scripts scripts
COPY sql sql
COPY .streamlit .streamlit
RUN useradd --uid 10001 --create-home appuser
USER appuser
EXPOSE 8000 8501
CMD ["uvicorn", "backend.api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
