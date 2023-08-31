FROM python:3.11.5-slim-bookworm
# -----------------------------------------
# We use the "stable" debian release; python does not seem to release current
# versions on LTS debian releases.

# We don't upgrade, and we pin all os dependency versions
RUN apt-get update && \
    apt-get install -y --no-install-recommends zip=3.0-13 unzip=6.0-28 bzip2=1.0.8-5+b1 libmagic-dev=1:5.44-3 htop=3.2.2-2 wget=1.21.3-1+b2 && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/bash", "-c"]

RUN mkdir -p /app

WORKDIR /app

# Standard simplified python setup.
COPY ./requirements.txt /app/requirements.txt
COPY ./requirements_dev.txt /app/requirements_dev.txt
RUN python -m pip install "pip==23.2.1" && pip install -r /app/requirements.txt -r /app/requirements_dev.txt

ENV PATH="/app:${PATH}"

# Run as a regular user, not root.
RUN addgroup --system kbapp && \
    adduser --system --ingroup kbapp kbapp && \
    chown -R kbapp:kbapp /app

USER kbapp

ENTRYPOINT [ "/app/development/tools/runner/entrypoint.sh" ]

CMD [ "bash" ]