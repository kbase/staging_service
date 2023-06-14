FROM python:3.11.4-slim-buster
# -----------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends zip=3.0-11+b1 unzip=6.0-23+deb10u3 bzip2=1.0.6-9.2~deb10u2 libmagic-dev=1:5.35-4+deb10u2 htop=2.2.0-1+b1 wget=1.20.1-1.1 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

RUN mkdir -p /app && chmod -R a+rw /app

WORKDIR /app

# Standard simplified python setup.
COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install "pip==23.1.2" && pip install -r /app/requirements.txt

COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log    

ENV PATH="/app:${PATH}"

ENTRYPOINT [ "/app/development/tools/runner/entrypoint.sh" ]

CMD [ "bash" ]