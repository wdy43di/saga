FROM python:3.12-slim

# We'll use /app as the standard working directory
WORKDIR /app

# Install dependencies directly to keep the image slim
RUN pip install --no-cache-dir flask requests

# Copy the server script into the root of /app
COPY saga_server.py /app/

# Copy your existing prompts and static files into the image
# This ensures the image works even without external volumes
COPY prompts /saga/prompts/
COPY static /app/static/

EXPOSE 8000

# Environment defaults (can be overridden by docker-compose)
ENV OLLAMA_URL="http://saga-ollama:11434"
ENV SAGA_MODEL="llama3:latest"

# Run the server
CMD ["python", "saga_server.py"]
