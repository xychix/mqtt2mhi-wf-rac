# Use an official lightweight Python base image
FROM python:3.11-slim

# Set the working directory
WORKDIR /app


# Copy the code and requirements
COPY klima_connector /app/klima_connector
COPY config /app/klima_connector/

# Install dependencies
RUN pip install --no-cache-dir -r klima_connector/requirements.txt

# Default command to run the script
CMD ["python", "klima_connector/klima_connector.py"]