# Runs one archiver pass per invocation (schedule it with cron/systemd/the orchestrator).
FROM python:3.12-slim
RUN useradd --system --create-home --home-dir /var/lib/openNASR-archiver opennasr
WORKDIR /src
COPY pyproject.toml README.md LICENSE ./
COPY openNASR ./openNASR
COPY contract ./contract
COPY archiver ./archiver
RUN pip install --no-cache-dir . ./contract "./archiver[s3]"
USER opennasr
ENV OPENNASR_CACHE_DIR=/var/lib/openNASR-archiver/cache \
    OPENNASR_STATE_FILE=/var/lib/openNASR-archiver/state.json
VOLUME /var/lib/openNASR-archiver
ENTRYPOINT ["openNASR-archiver"]
CMD ["run"]
