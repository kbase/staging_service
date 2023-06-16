# Testing

## In Container

You can run tests in a container which uses the same base image and uses the same dependencies. (This container can also run other python tasks.)

```shell
./development/scripts/run run_tests.sh
```

To run tests in individual test file you may supply the path to it. By default, the tests run against `tests/`.

```shell
./development/scripts/run run_tests.sh tests/test_app.py
```

## On Host

### install or activate python 3.11

E.g. macOS with macports:

```shell
sudo port install python311
sudo port select --set python python311
```

### install venv

```shell
python -m venv venv
```

### update pip

```shell
python -m pip install --upgrade pip
```

## Running Dev Server

For integration tests, the server can be stood up inside a docker container:

```shell
./development/scripts/run-dev-server.sh
```

### install deps

```shell
pip install -r requirements.txt
```

### run tests

```shell
./run_tests.sh
```

### Other

#### cherrypick tests

e.g. to just test app.py:

```shell
./run_tests.sh tests/test_app.py
```

#### coverage

check coverage in `htmlcov/index.html`
