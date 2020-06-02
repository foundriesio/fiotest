#!/bin/sh -e

HERE=$(dirname $(readlink -f $0))

MESSAGE="install-post" RESULT="OK" CURRENT_TARGET="${HERE}/current-target" ${HERE}/aklite-callback.sh
