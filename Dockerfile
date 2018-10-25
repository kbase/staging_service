FROM python:3.6-slim-stretch
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y zip && \
    apt-get install -y unzip && \
    apt-get install -y bzip2


RUN apt-get install -y htop wget

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

COPY ./ /kb/module
COPY ./globus.cfg /etc/globus.cfg

#RUN mkdir -p /kb/deployment/lib/src/data/bulk/bsadkhin/
#RUN echo bsadkhin@gmail.com > /kb/deployment/lib/src/data/bulk/bsadkhin/.globus_id

RUN cp -r /kb/module/staging_service /kb/deployment/lib
RUN cp -r /kb/module/deployment /kb
RUN echo


EXPOSE 3000

WORKDIR /kb/deployment/lib

ENTRYPOINT ["/kb/deployment/bin/entrypoint.sh"]
