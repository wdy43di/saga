FROM python:3.12-slim

WORKDIR /app

# 1. Install system dependencies (needed for some python wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. Copy and install Python requirements
# Doing this before copying code allows Docker to cache the layers
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Download NLTK data to a central location
RUN python -m nltk.downloader -d /usr/local/share/nltk_data \
    punkt \
    punkt_tab \
    averaged_perceptron_tagger \
    averaged_perceptron_tagger_eng

# 4. Set up the hearth structure
RUN mkdir -p /saga/prompts /saga/memory /app/static

# 5. Environment & Networking
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# Note: Code and memories are mounted via volumes in docker-compose 
# for fluidity during development/migration.
CMD ["python", "saga_server.py"]
