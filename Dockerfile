# Private deployment image: contains the mandatory contest catalogue. Do not publish.
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS catalogue-build
WORKDIR /catalogue
COPY scripts/unpack_catalogue.py ./unpack_catalogue.py
COPY data/catalogue.sqlite.xz data/catalogue-build.json ./
RUN python unpack_catalogue.py --source catalogue.sqlite.xz --manifest catalogue-build.json --output catalogue.sqlite

FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:6a0e06f5ba0b373d051aabd3fffb9b873f27f9a2a3a14bcbe37dee6f0e3bbc70 AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/backend \
    CATALOGUE_DB_PATH=/app/data/catalogue.sqlite STATE_DB_PATH=/data/state.sqlite
WORKDIR /app
COPY requirements.lock ./
RUN pip install --no-cache-dir --require-hashes -r requirements.lock \
    && groupadd --gid 10001 app && useradd --uid 10001 --gid app --no-create-home app \
    && mkdir /data && chown app:app /data
COPY backend/torob/ backend/torob/
COPY frontend/dist/ frontend/dist/
COPY --from=catalogue-build --chmod=444 /catalogue/catalogue.sqlite data/catalogue.sqlite
RUN chmod 755 /app/data
COPY --chmod=444 scripts/container_entrypoint.py scripts/container_entrypoint.py
USER 0:0
ENTRYPOINT ["python", "/app/scripts/container_entrypoint.py"]
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz',timeout=3)"
CMD ["uvicorn", "torob.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
