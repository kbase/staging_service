# Maintaining Dockerfile

## Base Image

The Base Image should be an official Python distribution. We should prefer the most
recent release, when possible.

## OS version

The OS should be debian, as debian/ubunto are widely used at KBase. The version should
be the current stable. The LTS version, which is often several versions behind stable,
does not seem to be supported by recent Python distributions. That is, to get the most
recent Python versions requires we can't use LTS, and conversely if we wished to use the
LTS debian we wouldn't be able to use the most recent Python releases.

It is more important to have a current Python, than a current OS. The OS really isn't
much of a concern to the service, as long as the required OS-level dependencies are
available. Python itself takes care of the interface to the OS, and that is all we are
concerned with.

## OS dependencies

The OS dependencies are indicated in the Dockerfile as exact versions. This ensures that
images are consistent, even as the base image evolves over time. 

## Different Dockerfiles

At present, there are three Dockerfiles which must be kept in synchrony. They differ
enough that the inconvenience of keeping them consistent seems worth the effort.

- `./Dockerfile`
    - used for the production image
    - needs to copy all service files
    - does not include development Python dependencies
    - has the production entrypoint
- `./.devcontainer/Dockerfile` 
    - used for the devcontainer workflow
    - does not copy service files
    - contains development Python dependencies
    - no entrypoint as that is provided by the docker-compose.yml
- `./development/tools/Dockerfile`
    - used for the host cli tools
    - does not copy service files
    - contains development Python dependencies
    - has special entrypoint which execs whatever command is passed from the command
      line
    

