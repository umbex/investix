FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir fastapi==0.128.0 pydantic-settings==2.12.0 "uvicorn[standard]==0.40.0" psycopg[binary]==3.2.13
COPY app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
