fiotest provides a base that can be extended for users of a Foundries Factory
to easily add testing.

## How It Works

Devices in a Factory communicate through a device gateway API. This API allows
device's to upload test results for the current Target the device is running.

fiotest can be run as Compose Application on devices in your fleet. The
application consists of 3 key pieces:

 * Aktualizr-lite callback handler that controls when testing is performed
 * A testing specification that defines *what* to test
 * A "spec runner" that executes the testing specification

## Aktualizr-lite callback handler

When the container is started, it will ensure that aktualizr-lite is configured
to send callback messages to it. The container then listens for 2 callbacks:

 * install-post "OK" - This means a new Target has been installed. The
   testing specification should be executed.

 * install-pre - This means an install is about to be started. If testing is
   running, it will be stopped.

## Testing Specification

A testing specification allows a user to define how target testing should
take place. Some users may want to do a single set of tests like:
~~~
# this runs the smoke test suite one time after a Target is installed
sequence:
  - tests:
      - name: smoke test
        command:
          - /usr/share/fio-tests/smoke.sh
~~~

Some users may want to do repeated "soak" testing of a device:
~~~
# run smoke test suite over and over taking a 10 minute break in between tests
sequence:
  - tests:
      - name: smoke test
        command:
          - /usr/share/fio-tests/smoke.sh
    repeat:
      delay_seconds: 600
~~~

A test can also be repeated a specific number of times:
~~~
# run smoke test suite 4 times with a 5 second delay between runs
sequence:
  - tests:
      - name: smoke test
        command:
          - /usr/share/fio-tests/smoke.sh
    repeat:
      delay_seconds: 5
      total: 4
~~~

A test can even force the device to reboot with:
~~~
# Run the smoke suite, reboot, and run it again
sequence:
  - tests:
      - name: smoke test
        command:
          - /usr/share/fio-tests/smoke.sh
  - reboot:
      command: /sbin/reboot
  - tests:
      - name: smoke test
        command:
          - /usr/share/fio-tests/smoke.sh
~~~

A test can be run directly on the host with:
~~~
sequence:
  - tests:
      - name: dmesg
        on_host: true
        command:
          - /bin/dmesg
~~~

## How to extend

1. Decide on approach to testing. The fiotest container can do a lot including
   running tests on the host OS. However, creating a container based on
   hub.foundries.io/lmp/fiotest might be needed for customized tests.
2. Create a custom test-spec.yml.
3. Update docker-compose.yml to reference 1 and 2.

### Example extension - add LTP test suite

#### Create LTP execution script - tests/ltp.sh
~~~
#!/bin/bash -e

set -o pipefail

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
~~~

#### Create Dockerfile extending fiotest
~~~
# Build LTP
FROM ubuntu:20.04 as ltp

RUN apt update && \
       apt install -y gcc git make pkgconf autoconf automake bison flex m4 libc6-dev wget

RUN wget -O /ltp.tar.xz https://github.com/linux-test-project/ltp/releases/download/20200515/ltp-full-20200515.tar.xz
RUN tar -xf /ltp.tar.xz
RUN    cd ltp-full* && \
       ./configure && \
       make -j8 all && \
       make install

RUN cd /opt/ltp/testcases/bin && \
       (strip `ls | grep -v .sh | grep -v .py` || true)

# Extend fiotest
FROM hub.foundries.io/lmp/fiotest:postmerge

COPY --from=ltp /opt/ltp /opt/ltp
COPY ./tests/ltp.sh /usr/share/fio-tests/ltp.sh
~~~

#### Add LTP to test-spec.yaml
~~~
sequence:
    tests:
...
      - name: ltp
         command:
          - /usr/share/fio-tests/ltp.sh
...
~~~
