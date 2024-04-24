# Scripts

## `generate-data-files.py`

A small tool, an example function really, to generate files for manual testing of upload and download. I use it by copy/pasting into a Python REPL session in the directory in which I want to generate files, and just run the function with the required parameters.

## `list-uploads.sh`

Handy for listing the contents of the `./data` directory while developing the `/upload` endpoint of the server locally. It simply lists the directory every 0.5s.

## `run`

Runs the Docker container located in /development/tools/runner with docker compose. This is a "runner container" designed to run things inside a container which is very similar to the service container. It is used to run tests, and can be used to run code quality tools also like black and mypy (not yet used in this project.)

The advantage of using `run` is that one does not have to arrange the precise version of Python and OS dependencies in a virtual environment.

Here are some usages of it:

To run mypy against the codebase:

```shell
./development/run mypy staging_service
```

To run black against the codebase:

```shell
./development/run black staging_service
```

To run black against the codebase and apply formatting fixes:

```shell
./development/run black staging_service  --fix
```