FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libssl-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build liboqs and liboqs-python from source, since there might not be a precompiled wheel for standard pip
# Setting up standard liboqs
RUN git clone -b main https://github.com/open-quantum-safe/liboqs.git && \
    cd liboqs && \
    mkdir build && cd build && \
    cmake -DBUILD_SHARED_LIBS=ON .. && \
    make -j4 && make install && \
    cd ../.. && rm -rf liboqs

# Set environment variable to help Python find standard liboqs
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "3002"]
