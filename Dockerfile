FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (including tesseract for pytesseract)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY apps/pkm-indexer/requirements.txt ./requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Make sure folders exist
RUN mkdir -p pkm/Inbox pkm/Processed/Metadata pkm/Processed/Sources pkm/Logs

# Expose the port your FastAPI app runs on
EXPOSE 8000

# Set the working directory to the app location
WORKDIR /app/apps/pkm-indexer

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]