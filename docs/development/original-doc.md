# staging_service

In order to setup local development, you must have docker installed and if you want to
run it locally you must have python 3.11.5 or greater installed

## setup

make a folder called /data as well as inside that /bulk and inside that a folder for any
usernames you wish it to work with

data
    -bulk
        -username
        -username

if you want to run locally you must install requirements.txt for python3

## running

to run locally run `/deployment/bin/entrypoint.sh`

to run inside docker run `/run_in_docker.sh`

to run in coordination with the kbase-ui development proxy, enabling it to serve locally
as a back end for Narrative, kbase-ui and other services:

```shell
make run-dev
```

## tests

### Run on host

- to test use `./run_tests.sh`
- requires python 3.11.5 or higher
- requires installation on mac of libmagic `brew install libmagic` or `sudo port install
  libmagic`

### Run in container

You can also run tests in a container which uses the same base image and uses the same
dependencies. (This container can also run other python tasks.)

```shell
./development/scripts/run run_tests.sh
```

To run tests in individual test file you may supply the path to it. By default, the
tests run against `tests/`.

```shell
./development/scripts/run run_tests.sh tests/test_app.py
```

## debugging

Included configurations for the Visual Studio Code debugger for python that mirror what
is in the entrypoint.sh and testing configuration to run locally in the debugger, set
breakpoints and if you open the project in VSCode the debugger should be good to go. The
provided configurations can run locally and run tests locally

## development

When releasing a new version:

- Update the release notes
- Update the version in [staging_service/app.py](staging_service/app.py).VERSION

## expected command line utilities

to run locally you will need all of these utils on your system: tar, unzip, zip, gzip,
bzip2, md5sum, head, tail, wc

in the docker container all of these should be available
