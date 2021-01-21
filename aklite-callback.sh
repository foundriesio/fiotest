#!/bin/sh -e

# This script can be called by aktualir-lite to handle its callbacks.
# It notifies the fiotest container about the callback so that it can
# handle everything.

# First make sure this app is still installed:
# aktualizr-lite "uninstalls" a compose-app by basically running:
#  docker-compose stop; rm -rf /var/sota/compose-apps/fiotest
# we can detect we were deleted by looking for that directory:
cd $(dirname $0)
if [ ! -d ./compose-apps/fiotest ] ; then
	if [ -f /etc/sota/conf.d/z-90-fiotest.toml ] ; then
		echo "fiotest appears to be removed. disabling callback"
		rm /etc/sota/conf.d/z-90-fiotest.toml
	fi

	# this gets tricky: we need to restart aklite. We don't want to do
	# it when aklite is performing an update. To be safe we just exit
	# now and eventually aklite will restart and stop calling us.
	exit 0
fi

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
