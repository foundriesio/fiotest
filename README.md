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
# this runs the LTP test suite one time after a Target is installed
sequence:
  - tests:
      - name: ltp
        command:
          - /usr/share/fio-tests/ltp.sh
~~~

Some users may want to do repeated "soak" testing of a device:
~~~
# run LTP test suite over and over taking a 10 minute break in between tests
sequence:
  - tests:
      - name: ltp
        command:
          - /usr/share/fio-tests/ltp.sh
    repeat:
      delay_seconds: 600
~~~

A test can also be repeated a specific number of times:
~~~
# run LTP test suite 4 times with a 5 second delay between runs
sequence:
  - tests:
      - name: ltp
        command:
          - /usr/share/fio-tests/ltp.sh
    repeat:
      delay_seconds: 5
      total: 4
~~~

A test can even force the device to reboot with:
~~~
# Run the LTP suite, reboot, and run it again
sequence:
  - tests:
      - name: ltp
        command:
          - /usr/share/fio-tests/ltp.sh
  - reboot:
      command: /sbin/reboot
  - tests:
      - name: ltp
        command:
          - /usr/share/fio-tests/ltp.sh
~~~

## How to extend

1. Create a container based on hub.foundries.io/fiotest with custom tests.
2. Create a custom test-spec.yml.
3. Update docker-compose.yml to reference 1 and 2.
