# Boilerplate makefile that minimally makes a docker image
#
# Author: Steve Chan sychan@lbl.gov
#

all: docker_image

docker_image:
	IMAGE_NAME="kbase/staging_service" hooks/build
