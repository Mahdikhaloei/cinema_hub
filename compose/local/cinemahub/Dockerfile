# define an alias for the specific python version used in this file.
FROM python:3.11.3-slim-bullseye as python

# Python build stage
FROM python as python-build-stage

RUN apt-get update && apt-get install --no-install-recommends -y build-essential libpq-dev

COPY ./requirements .

# Create Python Dependency and Sub-Dependency Wheels.
RUN pip wheel --wheel-dir /usr/src/app/wheels -r local.txt


# Python 'run' stage
FROM python as python-run-stage

ARG APP_HOME=/app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV BUILD_ENV local

WORKDIR ${APP_HOME}

# Install required system dependencies
RUN apt-get update && apt-get install --no-install-recommends -y libpq-dev gettext \
  # cleaning up unused files
  && apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false \
  && rm -rf /var/lib/apt/lists/*

# All absolute dir copies ignore workdir instruction. All relative dir copies are wrt to the workdir instruction
# copy python dependency wheels from python-build-stage
COPY --from=python-build-stage /usr/src/app/wheels  /wheels/

# use wheels to install python dependencies
RUN pip install --no-cache-dir --no-index --find-links=/wheels/ /wheels/* \
	&& rm -rf /wheels/

COPY ./compose/local/cinemahub/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint
RUN chmod +x /entrypoint

COPY ./compose/local/cinemahub/start /start
RUN sed -i 's/\r$//g' /start
RUN chmod +x /start


# copy application code to WORKDIR
COPY . ${APP_HOME}
WORKDIR ${APP_HOME}/core

ENTRYPOINT ["/entrypoint"]
