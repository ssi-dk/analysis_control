FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8
LABEL maintainer="Finn Gruwier Larsen <figl@ssi.dk>"

RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py | python -
COPY pyproject.toml /pyproject.toml
RUN /root/.local/bin/poetry install

COPY ./app /app