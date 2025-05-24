FROM python:3.10-slim

WORKDIR /app

# Install CUDA dependencies for GPU support
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install email-validator pydantic[email]

ARG PASSED_HUGGINGFACE_TOKEN

# Set environment variables for Mistral
ENV USE_MISTRAL=true
ENV MISTRAL_MODEL_PATH=/app/mistral_models
ENV HUGGINGFACE_TOKEN=${PASSED_HUGGINGFACE_TOKEN}

# Create directory for Mistral model
RUN mkdir -p /app/mistral_models

# Pre-authenticate with Hugging Face
RUN pip install huggingface_hub && \
    python -c "import os; from huggingface_hub import login; token = os.getenv('HUGGINGFACE_TOKEN'); login(token=token)"

# Copy all files to the app directory
COPY . .

# Create an empty __init__.py file to make it a package
RUN touch __init__.py

EXPOSE 8000

# Start the application with python module notation
CMD ["python", "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"] 