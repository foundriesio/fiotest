#!/bin/sh -e

# This script can be called by aktualir-lite to handle its callbacks.
# It notifies the fiotest container about the callback so that it can
# handle everything.

data="${MESSAGE},${CURRENT_TARGET}"
if [ -n "$RESULT" ] ; then
	data="${data},${RESULT}"
fi

# After a platform install, the system will reboot and aktualizr-lite will
# start before docker gets the container up and running. This adds some
# back-off logic so that we don't miss aktualizr-lite's install-post message
# that will trigger a new test run.
for i in 1 2 4 8 16 ; do
	if wget -O- -q --post-data="${data}" http://localhost:8000/ ; then
		exit 0
	fi
	echo "Callback failure, retrying in $i seconds"
	sleep $i
done
echo "Unable to notify callback"
exit 1
