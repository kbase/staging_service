FROM python:3.6-slim-stretch
# -----------------------------------------
RUN mkdir -p /kb/deployment/lib
COPY ./ /kb/module

# RUN mkdir -p /kb/module && \
#     cd /kb/module && \
#     git clone https://github.com/kbase/staging_service && \
#     cd staging_service && \
#     rm -rf /kb/deployment/lib/staging_service && \
    # cp -vr ./ /kb/deployment/lib/staging_service
RUN pip install -r /kb/module/requirements.txt

RUN cp -r /kb/module/staging_service /kb/deployment/lib

EXPOSE 3000

WORKDIR /kb/deployment/lib

ENTRYPOINT [ "python", "-m", "staging_service" ]
