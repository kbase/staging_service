# Development Tools

This document provides an overview of two different but related development approaches -
devcontainers (via Visual Studio Code), and command line tools via a Docker container.

## Visual Studio Code devcontainer

One of your best friends for development may be Visual Studio Code (VSC) and a devcontainer.
This repo contains a VSC devcontainer all ready for use.

> At the time of writing, devcontainer support for PyCharm is not mature enough to use;
> too many features are missing. However, in the near future this should also be a very
> productive development environment.

A devcontainer provides a stable, reproducible development platform. For this repo, it
is based on the Python 3.11 debian image, the same one used for deployment. In fact, the
devcontainer should reflect the same OS and Python environment as the deployment and the
development tools images. This feature is important for reproducibility, and providing
the least surprise!

There is also support for locally hosted development via VSC, but this developer (EAP)
does not do this style of Python development.

### Getting Started

1. Ensure you have docker running.

2. Open the project in VSC

    There are a few ways to open a project in VSC:

    - from the repo directory `code .`
    - from VSC menu:
    - File > New Window
    - From the new window:
        - Click on Explorer in the left-nav, then click on Open Folder
        - or
        - Selecte File > Open Folder
    - Select the folder containing the repo (project)
    - Click Open

3. Start the devcontainer.

    - press the keys `Shift` - `Command` - `P` (macOS) to open the command palette
    - start typing "Dev Container: Reopen Folder in Container"
    - when you see it appear, click on it
    - the image will build, the container will start

4. Open a terminal

    If a terminal is not already open, open the built-in terminal with `Control` - `~`
    (that is a tilde)

5. Depending on the docker installation, you may need to grant access. If you don't see
   git things enabled, click on the Git tool, and follow the instructions.

Now you should treat this just like a local environment. The Python dependencies will
already be installed. If you have changes to them, however, you may simply make the
change to the requirements file and then reinstall them from the VSC devcontainer
terminal.

### Running Tools

All of the tools available for running from the host via docker are also directly
available within the devcontainer. I still often run them from a host termianl anyway, as
I can control the position and display of the native terminal a bit better, and it is
also decoupled from any issues VSC may have. YMMV.

Here are the common ones:

- `mypy staging_service`
- `black staging_service`
- `isort staging_service`
- `./run_tests.sh`

### Running the server

It is very efficacious to develop the server as it is running, and to exercise new or
changed endpoints directly. This can be through a local host and port, or via kbase-ui
integration and an official kbase environment host.

In either case, the startup of the service is the same:

```shell
FILE_LIFETIME="90" KB_DEPLOYMENT_CONFIG="${PWD}/deployment/conf/local.cfg" PYTHONPATH="${PWD}/staging_service" python -m staging_service
```

The `FILE_LIFETIME` environment variable is required, and sets the file retention policy.

We ensure that the configuration is available via `KB_DEPLOYMENT_CONFIG`. In our case we
are using a configuration file already prepared for local usage. If you inspect it,
you'll find that all directory references are relative to the current directory. We are
referecing the `local.cfg` local configuration where it is stored in the codebase.

We also ensure that the `staging_service` is included in the `PYTHONPATH`.

Finally, we invoke the service simply by starting the bare aiohttp server invocation
located in `staging_service/__main__.py`.

As a quick sanity test once the service is running, try this from a host terminal:

```shell
curl http://localhost:3000/test-service
```

> TODO: The service should have a `/status` endpoint, not `/test-service`.

## Host Tools

The code checking tools can all be run from the host via the `run` script. This script
actually runs the tools in a Docker container which is very similar to the devcontainer
and service Docker configurations.

To run the tools:

- `./development/scripts/run mypy staging_service`
- `./development/scripts/run black staging_service`
- `./development/scripts/run isort staging_service`
- `./development/scripts/run ./run_tests.sh`
