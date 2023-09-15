# KBase Staging Service

## Background

The staging service provides an API to a shared filesystem designed primarily to
allow KBase users to upload raw data files for usage by KBase apps within a Narrative.
The API allows for uploading, decompressing and downloading files. In addition it
provides some utility for Globus transfer integration into the filesystem.

The `staging_service` is a core KBase service designed to be run within the KBase
infrastructure. The runtime requires access to other KBase services as well as a
suitable filesystem. Internal libraries implement the interfaces to these services,
which are all open source and documented in their respective repos.  In a break from the
traditional KBase service, it is not based on the KBase SDK, but rather `aiohttp`.

For more about how data import works from the user perspective, please [refer to the KBase
documentation](https://docs.kbase.us/getting-started/narrative/add-data).

## Installation

The service is designed to be packaged into a Docker image and run as a container.

For deployment, the image is built by GitHub actions and stored in GitHub Container
Registry.

For local development and evaluation, it may be run locally from within a devcontainer,
or from a locally-built image.

> TODO: provide barebones instructions here

## Usage

There are three basic usage scenarios - development, local deployment, and production
deployment.

Development has [its own documentation](./docs/development/inde.md).

Production deployment is out of scope (though it can be larged deduced from local
deployment).

Local deployment is as easy as running

```shell
./scripts/run-dev-server.sh
```

from within the devcontainer.

## API

See [the API documentation](./docs/api.md).

## Contributing

This repo is realistically only open to contributions from users within the KBase
organization. The contribution model is Pull Requests make from branches off of main. So
clearly one needs to have the ability to push up branches and create PRs.

Forks are not supported at this time.

## Development

For development support, see [the development docs](./docs/development.md)

## License

See [the KBase License](./LICENSE.md)
