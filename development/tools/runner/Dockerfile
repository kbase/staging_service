FROM python:3.11.4-slim-buster
# -----------------------------------------
RUN apt-get update && apt-get install -y zip unzip bzip2 libmagic-dev htop wget

SHELL ["/bin/bash", "-c"]

RUN mkdir -p /app && chmod -R a+rw /app

WORKDIR /app

# Standard simplified python setup.
COPY ./requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip && \
    pip install --upgrade setuptools && \
    pip install -r /app/requirements.txt

COPY ./globus.cfg /etc/globus.cfg
RUN touch /var/log/globus.log && chmod 777 /var/log/globus.log    

# ENV PATH="/root/.local/bin:$PATH"
# ENV PYTHONPATH="/kb/module/src"
ENV PATH="/app:${PATH}"

ENTRYPOINT [ "/app/development/tools/runner/entrypoint.sh" ]

CMD [ "bash" ]