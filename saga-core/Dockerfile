FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask requests
# ... existing pip installs ...
RUN pip install --no-cache-dir flask requests nltk

# Explicitly download all required grammar components to the correct path
RUN python -m nltk.downloader -d /usr/local/share/nltk_data punkt punkt_tab averaged_perceptron_tagger averaged_perceptron_tagger_eng

# We create the directories, but we WON'T copy the files yet
# We want the volumes in docker-compose to handle the "live" code
RUN mkdir -p /saga/prompts /saga/memory /app/static

# Force logs to show up in terminal
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["python", "saga_server.py"]
