# Start from a standard Python 3.11 image
FROM python:3.11-slim

# Set a working directory inside the container
WORKDIR /app

# --- This is the magic part ---
# Install the system-level programs our app needs
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Copy our requirements file into the container
COPY requirements.txt .

# Install all our Python libraries
RUN pip install --no-cache-dir -r requirements.txt

# Download the NLTK data (punkt and punkt_tab)
RUN python -m nltk.downloader punkt punkt_tab

# Copy the rest of our app code into the container
COPY . .

# Tell the world that our app runs on this port
# Render will automatically use this port
EXPOSE 10000

# The command to run our app using the Gunicorn server

CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]
