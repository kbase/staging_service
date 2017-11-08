# staging_service

setup local development

must have docker installed

if you want to run it locally you must have python3.6 installed


# setup

make a folder called /data as well as inside that /bulk and inside that a folder for any usernames you wish it to work with

data
    -bulk
        -username
        -username


if you want to run locally you must install requirements.txt for python3

# running

to run locally run /deployment/bin/entrypoint.sh

to run inside docker run /run_in_docker.sh

to run tests TODO

# debugging

Included configurations for the Visual Studio Code debugger for python that mirror what is in the entrypoint.sh and testing configuration to run locally in the debugger, set breakpoints and if you open the project in VSCode the debugger should be good to go. The provided configurations can run locally and run tests locally