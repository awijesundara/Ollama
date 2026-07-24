FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app app

COPY pyproject.toml README.md requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt

COPY src ./src
RUN python -m pip install --no-cache-dir --no-deps .

COPY app.py ./
COPY .chainlit ./.chainlit
COPY public ./public
COPY docker/app-entrypoint.sh /usr/local/bin/app-entrypoint

RUN chmod 0755 /usr/local/bin/app-entrypoint \
    && mkdir -p /data/users /run/app-secrets \
    && chown -R app:app /app /data /run/app-secrets

USER app

EXPOSE 8000

ENTRYPOINT ["app-entrypoint"]
CMD ["chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8000"]
