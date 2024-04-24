# Maintaining Dockerfile

## Base Image

The Base Image should be an official Python distribution. We should prefer the most
recent release, when possible.

## OS version

The OS should be Debian, as Debian/Ubuntu are widely used at KBase. The version should
be the current stable. The LTS version, which is often several versions behind stable,
does not seem to be supported by recent Python distributions. That is, if we want to get
recent Python versions we probably can't use LTS, and conversely if we wished to use the
LTS debian we wouldn't be able to use the most recent Python releases.

It is more important to have a current Python, than a current OS. The OS really isn't
much of a concern to the service, as long as the required OS-level dependencies are
available. Python itself takes care of the interface to the OS, and that is all we are
concerned with.

## OS dependencies

The OS dependencies are indicated in the Dockerfile as exact versions. This ensures that
images are consistent, even as the base image evolves over time. We should keep an eye
on this, as there are reports from some Linux distros (e.g. Alpine) that package
retention is not permanent, and older packages may eventually be dropped, meaning that a
future build may actually fail if it pins package versions. There is some controversy
over this, with distro maintainers complaining that they dont' have infinite storage
space for all package versions they have distributed.

## Dockerfile Design

The Dockerfile serves at least three purpopses. Its design reflects this by utilizing a
multi-stage build. Multi-stage builds are primarily for creating internal build layers
that can be omitted from the final image. However, in this case we use this design to
create a base image with most OS and Python dependencies installed, a dev stage which
has development dependencies (OS and Python) installed, and finally a production stage
which adds all runtime files and the entrypoint.

The dev stage is used by the devcontainer and tool docker-compose files to run a
container which is all ready for development, just needing the repo to be volume mounted
at `/kb/module``.

The production deploy image can be exercised with the top level `docker-compose.yml`.
