FROM python:3.11.5-slim-bookworm AS base
# -----------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends zip=3.0-13 unzip=6.0-28 bzip2=1.0.8-5+b1 libmagic-dev=1:5.44-3 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt /kb/requirements.txt
RUN python -m pip install "pip==23.2.1" && pip install -r /kb/requirements.txt && rm -r /kb

# The BUILD_DATE value seem to bust the docker cache when the timestamp changes, move to
# the end
LABEL org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.vcs-url="https://github.com/kbase/staging_service.git" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.schema-version="1.1.8" \
    us.kbase.vcs-branch=$BRANCH \
    maintainer="Steve Chan sychan@lbl.gov"

#
# Dev Layer 
# Used in devcontainer, and as base for tools
#
FROM base AS dev
# Install OS dependencies required by or nice-to-have in a development image
RUN apt-get update && \
    apt-get install -y --no-install-recommends htop=3.2.2-2 wget=1.21.3-1+b2 git=1:2.39.2-1.1 openssh-client=1:9.2p1-2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
# Install Python dependencies require by development tools (cli tools and devcontainer)
COPY ./requirements_dev.txt /kb/requirements_dev.txt
RUN pip install -r /kb/requirements_dev.txt && rm -r /kb
WORKDIR /kb/module
# Note - entrypoint defined in docker compose file, and /kb/module is volume mounted by
# the devcontainer and the tools

#
# Prod layer
#
FROM base AS prod

# Install globus configuration into expected location.
# TODO: point to location for documentation of this.
COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log

# We expect this to run on port 3000
# TODO: this is weird, kbase services usually run at port 5000.
EXPOSE 3000

# We keep the entire repo in /kb/module; for why, I know not.
# TODO: could someone add a comment here explaining why?
COPY ./ /kb/module
WORKDIR /kb/module

# Otherwise, the service is installed in /kb/deployment (!)
# RUN mkdir -p /kb/deployment/lib
# RUN cp -r /kb/module/staging_service /kb/deployment/lib

#
# Here we copy all of the required runtime components that need 
# to be in the image.
#

# This contains the entrypoint
COPY ./deployment/bin /kb/deployment/bin

# This contains the CI deployment 
# TODO: why is it copied to the codebase, though?
COPY ./deployment/conf/deployment.cfg /kb/deployment/conf/deployment.cfg

# Configuration for mapping file extensions to importers
COPY ./deployment/conf/supported_apps_w_extensions.json /kb/deployment/conf/supported_apps_w_extensions.json

# The service code.
COPY ./staging_service /kb/deployment/lib/staging_service

ENTRYPOINT ["/kb/module/deployment/bin/entrypoint.sh"]
