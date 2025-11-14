# Multi-stage Dockerfile for Cryptocurrency Trading Terminal
# Supports both development and production builds

# Base stage with Python and Flutter SDK
FROM ubuntu:22.04 as base

# Avoid interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Shanghai

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    xz-utils \
    zip \
    openjdk-11-jdk \
    python3 \
    python3-pip \
    python3-venv \
    locales \
    libgtk-3-0 \
    libnotify4 \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xauth \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set up Python 3.14
RUN curl -sSL https://www.python.org/ftp/python/3.14.0/Python-3.14.0.tgz -o python3.14.tgz \
    && tar -xzf python3.14.tgz \
    && cd Python-3.14.0 \
    && ./configure --enable-optimizations --prefix=/usr/local \
    && make -j$(nproc) \
    && make install \
    && rm -rf /tmp/* \
    && python3.14 --version

# Set up Flutter
ENV PATH="/opt/flutter/bin:$PATH"
ENV FLUTTER_ROOT="/opt/flutter"
ENV FLUTTER_HOME="/opt/flutter"

RUN wget -q https://storage.googleapis.com/flutter_infra_release/releases/stable/linux/flutter_linux_3.24.3-stable.tar.xz \
    && tar xf flutter_linux_3.24.3-stable.tar.xz \
    && mv flutter /opt/ \
    && flutter config --no-analytics \
    && flutter doctor

# Set locale
RUN locale-gen en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LANGUAGE=en_US:en
ENV LC_ALL=en_US.UTF-8

# Development stage
FROM base as development

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt ./
RUN pip3.14 install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Install Flutter dependencies
RUN flutter pub get

# Expose port for development server (if needed)
EXPOSE 8000

# Default command for development
CMD ["bash"]

# Python backend stage
FROM base as backend

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt ./
RUN pip3.14 install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Create non-root user
RUN useradd -m -u 1000 tradinguser && chown -R tradinguser:tradinguser /app
USER tradinguser

# Expose FastAPI port
EXPOSE 8000

# Default command for backend
CMD ["python3.14", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Flutter frontend build stage
FROM development as flutter-build

# Build Flutter application
RUN flutter build linux --release

# Multi-stage build for final production image
FROM base as production

WORKDIR /app

# Copy built application
COPY --from=flutter-build /app/build/linux/x64/release/bundle ./app

# Copy backend if needed
COPY --from=backend /app/backend ./backend

# Install production dependencies only
COPY requirements.txt ./
RUN pip3.14 install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 tradinguser && chown -R tradinguser:tradinguser /app
USER tradinguser

# Expose ports
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["./app/trading_terminal"]