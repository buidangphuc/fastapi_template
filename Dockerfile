# Stage 1: Build dependencies
FROM python:3.12-slim AS build

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip -i https://pypi.org/simple \
    && pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime environment
FROM python:3.12-slim AS runtime

# Copying dependencies from build stage
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/bin /usr/local/bin

ENV PYTHONPATH=/usr/local/lib/python3.12/site-packages
ENV PATH="/usr/local/bin:$PATH"

# Set timezone
ENV TZ=Asia/Ho_Chi_Minh

# Create necessary directories
RUN mkdir -p /var/log/server /fpa/logs

# Set working directory
WORKDIR /fpa

# Copy application files
COPY . .

# Expose port
EXPOSE 8000

# Set default number of workers
ENV WORKERS=1

# Run application
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --workers ${WORKERS}"]
