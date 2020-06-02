#!/bin/sh -e

# This script can be called by aktualir-lite to handle its callbacks.
# It notifies the fiotest container about the callback so that it can
# handle everything.

data="${MESSAGE},${CURRENT_TARGET}"
if [ -n "$RESULT" ] ; then
	data="${data},${RESULT}"
fi
wget -O- -q --post-data="${data}" http://localhost:8000/
