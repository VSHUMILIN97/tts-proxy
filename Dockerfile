FROM python:3.7-slim-buster
RUN apt-get update && apt-get install sox netcat \
            python3.7-dev python-psycopg2 nginx ffmpeg \
            -y --no-install-recommends && \
            rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
WORKDIR /opt/imedgen
RUN mkdir -p /opt/imedgen/logs
COPY . ./
RUN pip install -r requirements.txt
RUN pip install -r lint-requirements.txt -r dev-requirements.txt
ENTRYPOINT ["entries/app_entry_dev.sh"]
