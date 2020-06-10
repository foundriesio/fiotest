#!/bin/bash -e

set -o pipefail

# require ipv6:
# bind04
# bind05

# really slow
# bind06
# fork13
# needs full blown "ps":
# msgstress04

# /dev/block/loop stuf
# chown04
fsmount01
fsmount02
fsopen01
fsopen02
fspick01
fspick02
fanotify13
fanotify14
fanotify15
fanotify16
lchown03
lchown03_16
linkat02
mknod07
mmap16
mount02
mount03
mount04
mount06
move_mount01
move_mount02

# crashes:
# creat05
# dup3
# fcntl12

TESTS="${TESTS-syscalls -s madvise}"
LTP_PATH="${LTP_PATH-/opt/ltp}"
LOGS="/tmp/LTP_$(date +%s)_"

[ -z $TEST_DIR ] && (echo "ERROR: TEST_DIR not defined"; exit 1)
[ -d $TEST_DIR ] || (echo "ERROR: no TEST_DIR"; exit 1)

read_ltp_results() {
	grep -E "PASS|FAIL|CONF"  "$1" \
		| awk '{print $1" "$2}'
}

failed=0
run_ltp() {
	cd "${LTP_PATH}"

	./runltp -p -q -f $TESTS -l "${LOGS}.log" 2>&1 | tee ${LOGS}-output.log || true
	while IFS= read -r line ; do
		parts=($line)
		result_dir="${TEST_DIR}/$(date +%s.%N)-${parts[0]}"
		mkdir ${result_dir}
		if [ "${parts[1]}" = "FAIL" ] ; then
			touch ${result_dir}/failed
			failed=1
		fi
		if [ "${parts[1]}" = "CONF" ] ; then
			touch ${result_dir}/skipped
		fi
	done < <(read_ltp_results "${LOGS}.log")
}

run_ltp
exit $failed
