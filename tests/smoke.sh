#!/bin/bash -e

set -o pipefail

TESTS="pwd, uname -a, lscpu, vmstat, lsblk"

[ -z $TEST_DIR ] && (echo "ERROR: TEST_DIR not defined"; exit 1)
[ -d $TEST_DIR ] || (echo "ERROR: no TEST_DIR"; exit 1)

indent() {
    sed 's/^/|  /'
    echo "|--"
}

run() {
    # shellcheck disable=SC2039
    local test="$1"
    test_case_id="$(echo "${test}" | awk '{print $1}')"
    result_dir="${TEST_DIR}/$(date +%s.%N)-${test_case_id}"
    mkdir ${result_dir}
    echo
    echo "Running ${test_case_id} test..."
    local exit_code=0
    eval "${test}" | indent || exit_code="$?"
    echo "Exit code: $exit_code"

    if [ "${exit_code}" -ne 0 ]; then
        touch ${result_dir}/failed
    fi
    return "${exit_code}"
}

failed=0
IFS=","
for test_cmd in $TESTS ; do
    return_code=0
    run "${test_cmd}" || return_code="$?"
    echo "Return code: $return_code"
    if [ "$return_code" -ne 0 ]; then
        failed=1
    fi
    TESTS="$(echo "${TESTS}" | sed -r "s#${test_cmd},? *##")"
done
exit $failed
