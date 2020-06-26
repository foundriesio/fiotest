#!/bin/bash -e

set -o pipefail

TESTS="${TESTS-mm}"
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
