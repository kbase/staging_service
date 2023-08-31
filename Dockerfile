FROM python:3.11.5-slim-bullseye
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
RUN apt-get update && \
    apt-get install -y --no-install-recommends zip=3.0-13 unzip=6.0-28 bzip2=1.0.8-5+b1 libmagic-dev=1:5.44-3 htop=3.2.2-2 wget=1.21.3-1+b2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY ./requirements.txt /requirements.txt
RUN python -m pip install "pip==23.2.1" && pip install -r /requirements.txt && rm /requirements.txt

COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log

COPY ./ /kb/module
RUN cp -r /kb/module/staging_service /kb/deployment/lib
RUN cp -r /kb/module/deployment /kb


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
