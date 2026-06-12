FROM ghcr.io/d4vinci/scrapling:latest

RUN pip install --no-cache-dir \
    pandas==2.2.3 \
    pyarrow==16.1.0 \
    python-jobspy==1.1.80 \
    requests==2.32.3
