FROM apache/airflow:2.10.4-python3.12

USER root

# Install system deps (Airflow basics + Playwright/Chromium libs)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    wget \
    xdg-utils \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Install Python dependencies directly (no requirements file needed)
RUN pip install --no-cache-dir \
    apache-airflow[postgres] \
    apache-airflow-providers-google \
    aiohttp \
    beautifulsoup4 \
    requests \
    lxml \
    httpx \
    langchain \
    langchain-community \
    langchain-google-genai \
    opensearch-py \
    pendulum \
    python-dateutil \
    tenacity \
    python-dotenv \
    playwright

# Install Playwright browser (as user; deps already installed)
RUN playwright install chromium

# Set working directory and Python path
WORKDIR /opt/airflow
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"

