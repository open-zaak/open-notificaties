# Stage 1 - Compile needed python dependencies
FROM python:3.7-stretch AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements /app/requirements
RUN pip install pip setuptools -U
RUN pip install -r requirements/production.txt


# Stage 2 - build frontend
FROM mhart/alpine-node:10 AS frontend-build

WORKDIR /app

COPY ./*.json /app/
RUN npm ci

COPY ./Gulpfile.js /app/
COPY ./build /app/build/

COPY src/nrc/sass/ /app/src/nrc/sass/
RUN npm run build


# Stage 3 - Build docker image suitable for execution and deployment
FROM python:3.7-stretch AS production

RUN apt-get update && apt-get install -y --no-install-recommends \
        postgresql-client \
        netcat \
    && rm -rf /var/lib/apt/lists/*

# Stage 3.1 - Set up the needed production dependencies
COPY --from=build /usr/local/lib/python3.7 /usr/local/lib/python3.7
COPY --from=build /usr/local/bin/uwsgi /usr/local/bin/uwsgi
COPY --from=build /usr/local/bin/celery /usr/local/bin/celery

# Stage 3.2 - Copy source code
WORKDIR /app
COPY ./bin/wait_for_db.sh /wait_for_db.sh
COPY ./bin/wait_for_rabbitmq.sh /wait_for_rabbitmq.sh
COPY ./bin/docker_start.sh /start.sh
COPY ./bin/celery_worker.sh /celery_worker.sh
COPY ./bin/celery_flower.sh /celery_flower.sh
RUN mkdir /app/log

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
