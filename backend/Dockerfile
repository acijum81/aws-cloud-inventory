FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir .
COPY src ./src
RUN groupadd --system app && useradd --system --gid app --no-create-home app && chown -R app:app /app
ENV PYTHONPATH=/app/src
USER app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
