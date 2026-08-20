FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements.txt \
    && python -m pip uninstall -y pip \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip \
    && rm -rf /usr/local/lib/python3.12/site-packages/pip-*.dist-info

COPY . .

EXPOSE 8000

CMD ["python", "main.py"]