FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    AUTH_DB_PATH=/data/auth.db

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src
COPY data ./data
RUN mkdir -p /data

EXPOSE 8501

CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0", "--server.headless=true"]
