FROM python:3.12-slim

ENV POETRY_VERSION=1.8.1
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PYTHONPATH=/app

WORKDIR /app

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION"

COPY pyproject.toml ./

RUN poetry install --no-interaction --no-ansi

COPY . .

RUN mkdir logs

CMD ["python", "Scripts/run.py"]
