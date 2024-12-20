# Stage 1 - Compile needed python dependencies
FROM python:3.11-slim-bookworm AS build

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        build-essential \
        libpq-dev \
        git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install pip "setuptools>=70.0.0"
RUN pip install -r requirements/production.txt


# Stage 2 - build frontend
FROM node:16-bookworm-slim AS frontend-build

WORKDIR /app

COPY ./*.json /app/
RUN npm ci --legacy-peer-deps

COPY ./Gulpfile.js /app/
COPY ./build /app/build/

COPY src/nrc/sass/ /app/src/nrc/sass/
RUN npm run build


# Stage 3 - Build docker image suitable for execution and deployment
FROM python:3.11-slim-bookworm AS production

RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends \
        media-types \
        procps \
        nano \
        curl \
        gettext \
        postgresql-client \
        # Required for Celery to work.
        netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

RUN pip install pip "setuptools>=70.0.0"

# Stage 3.1 - Set up the needed production dependencies
COPY --from=build /usr/local/lib/python3.11 /usr/local/lib/python3.11
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi
COPY --from=build /usr/local/bin/celery /usr/local/bin/celery

# Stage 3.2 - Copy source code
WORKDIR /app
COPY ./bin/wait_for_db.sh /wait_for_db.sh
COPY ./bin/wait_for_rabbitmq.sh /wait_for_rabbitmq.sh
COPY ./bin/docker_start.sh /start.sh
COPY ./bin/celery_worker.sh /celery_worker.sh
COPY ./bin/celery_flower.sh /celery_flower.sh
COPY ./bin/celery_beat.sh /celery_beat.sh
COPY ./bin/uninstall_adfs.sh ./bin/uninstall_django_auth_adfs_db.sql /app/bin/
COPY ./bin/check_celery_worker_liveness.py ./bin/
COPY ./bin/setup_configuration.sh /setup_configuration.sh
RUN mkdir /app/log /app/config /app/tmp

COPY --from=frontend-build /app/src/nrc/static/css /app/src/nrc/static/css
COPY ./src /app/src

RUN useradd -M -u 1000 opennotificaties
RUN chown -R opennotificaties /app

# drop privileges
USER opennotificaties

ARG COMMIT_HASH
ARG RELEASE
ENV GIT_SHA=${COMMIT_HASH}
ENV RELEASE=${RELEASE}

ENV DJANGO_SETTINGS_MODULE=nrc.conf.docker

ARG SECRET_KEY=dummy

# Run collectstatic, so the result is already included in the image
RUN python src/manage.py collectstatic --noinput

LABEL org.label-schema.vcs-ref=$COMMIT_HASH \
      org.label-schema.vcs-url="https://github.com/open-zaak/open-notificaties" \
      org.label-schema.version=$RELEASE \
      org.label-schema.name="Open Notificaties"

EXPOSE 8000
CMD ["/start.sh"]
