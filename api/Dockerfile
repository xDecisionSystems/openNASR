FROM python:3.12-slim
RUN useradd --system --create-home --home-dir /var/lib/openNASR-api opennasr
WORKDIR /src
COPY pyproject.toml README.md ./
COPY openNASR ./openNASR
COPY contract ./contract
COPY api ./api
RUN pip install --no-cache-dir . "./contract[s3]" ./api
USER opennasr
ENV OPENNASR_API_CACHE_DIR=/var/lib/openNASR-api/cache \
    OPENNASR_API_HOST=0.0.0.0
VOLUME /var/lib/openNASR-api
EXPOSE 8000
HEALTHCHECK CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/health')"
ENTRYPOINT ["openNASR-api"]
