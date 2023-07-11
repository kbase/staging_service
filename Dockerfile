FROM python:3.9-slim-buster
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y zip && \
    apt-get install -y unzip && \
    apt-get install -y bzip2 && \
    apt-get install -y libmagic-dev


RUN apt-get install -y htop wget

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./ /kb/module
COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log
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
