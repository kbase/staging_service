FROM python:3.11.4-slim-buster
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
RUN apt-get update && apt-get install -y zip unzip bzip2 libmagic-dev htop wget

# Standard simplified python setup.
COPY ./requirements.txt /requirements.txt
RUN python -m pip install --upgrade pip && pip install -r /requirements.txt

COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log

COPY ./staging_service /kb/deployment/lib/staging_service
COPY ./deployment /kb/deployment

# TODO: should be port 5000 to match other kbase services
EXPOSE 3000

WORKDIR /kb/deployment/lib

# The BUILD_DATE value seem to bust the docker cache when the timestamp changes, move to
# the end
LABEL org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.vcs-url="https://github.com/kbase/staging_service.git" \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.schema-version="1.1.8" \
    us.kbase.vcs-branch=$BRANCH \
    maintainer="Steve Chan sychan@lbl.gov"

ENTRYPOINT ["/kb/deployment/bin/entrypoint.sh"]
