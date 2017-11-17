FROM python:3.6-slim-stretch
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
COPY ./ /kb/module
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y zip && \
    apt-get install -y unzip && \
    apt-get install -y bzip2

RUN pip install -r /kb/module/requirements.txt

RUN cp -r /kb/module/staging_service /kb/deployment/lib
RUN cp -r /kb/module/deployment /kb

EXPOSE 3000

WORKDIR /kb/deployment/lib

ENTRYPOINT ["/kb/deployment/bin/entrypoint.sh"]
