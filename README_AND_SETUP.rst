
User Directory and Globus Identity File
=======================================
The user directory and globus token file is created upon all authenticated calls to the staging service.

More Details
============

`authorize_request():` grabs the token from the `kbase_session` or `kbase_session_backup` cookie or from the Authorization Header of the request and
then queries the KBase auth server to grab the username for the token. Then assert_globus_id is used to check to see if
the dtn:/data/bulk/username/ directory exists, and if the globus token file exists. If they do not, it creates it.

`globusid_exists():` uses the Path validator to validate a path and return a Path object. The PATH object gets configured when the staging area service starts up.
Paths are generated for the root directory for that user, and for that user's globus token file. These paths are used for the following step:

If the globus token file doesn't exist or is empty, the Auth service is queried for that user's globus id and
the first globus account's username is written to the globus token file
(Multiple linked globus accounts are not currently enabled.)


Local Testing in a Docker Container
===================================
* Make sure the COPY ./ step in the dockerfile is towards the end, so you won't need to rebuild the docker layers each time
* Copy directories and .globus_id files into the /data/bulk/ directory so the files will be in the appropriate place once the docker container starts
* For example /data/bulk/username/.globus_id (email@example.com)
* Make sure the globus.cfg contains the correct Endpoint Id, Client ID, and refresh tokens.
* Tokens can be obtained at https://globus-sdk-python.readthedocs.io/en/latest/tutorial/#advanced-2-refresh-tokens-never-login-again
