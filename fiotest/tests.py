import unittest
import yaml

from time import sleep
from unittest.mock import patch, MagicMock, PropertyMock

from fiotest.main import Coordinator
from fiotest.runner import SpecRunner
from fiotest.spec import TestSpec

SIMPLE_TEST_SPEC = """
sequence:
  - tests:
      - name: test1
        context:
            url: https://example.com/{LMP_FACTORY}/{CUSTOM_VERSION}/{LMP_MACHINE}
        command:
          - /bin/true
        on_host: true
      - name: test2
        command:
          - /bin/true
"""

class TestMain(unittest.TestCase):
    def setUp(self):
        data = yaml.safe_load(SIMPLE_TEST_SPEC)
        self.testspec = TestSpec.parse_obj(data)

    @patch("fiotest.host.sudo_execute", return_value=0)
    def test_coordinator_check_for_updates_pre(self, mock_sudo_execute):
        self.coordinator = Coordinator(self.testspec)
        self.assertEqual(False, self.coordinator.callbacks_enabled)
        self.assertEqual(True, self.coordinator.timer.is_alive())
        self.coordinator.on_check_for_updates_pre("foo")
        sleep(1)  # it takes a moment for thread to complete
        self.assertEqual(True, self.coordinator.callbacks_enabled)
        self.assertEqual(False, self.coordinator.timer.is_alive())

    @patch("fiotest.main.SpecRunner")
    @patch("fiotest.host.sudo_execute", return_value=0)
    def test_coordinator_on_install_post_ok(self, mock_sudo_execute, mock_specrunner):
        mock_runner = MagicMock()
        mock_specrunner.return_value = mock_runner
        type(mock_specrunner).reboot_state = PropertyMock(return_value="/foo/bar")

        self.coordinator = Coordinator(self.testspec)
        self.coordinator.on_check_for_updates_pre("foo")
        self.coordinator.on_install_post("foo", "OK")
        mock_specrunner.assert_called_once_with(self.testspec)
        mock_runner.start.assert_called_once()

    @patch("fiotest.main.SpecRunner")
    @patch("fiotest.host.sudo_execute", return_value=0)
    def test_coordinator_on_install_post_fail(self, mock_sudo_execute, mock_specrunner):
        mock_runner = MagicMock()
        mock_specrunner.return_value = mock_runner
        type(mock_specrunner).reboot_state = PropertyMock(return_value="/foo/bar")

        self.coordinator = Coordinator(self.testspec)
        self.coordinator.on_check_for_updates_pre("foo")
        self.coordinator.on_install_post("foo", "FAIL")
        mock_specrunner.assert_not_called()
        mock_runner.start.assert_not_called()

    @patch("fiotest.main.SpecRunner")
    @patch("fiotest.host.sudo_execute", return_value=0)
    def test_coordinator_on_install_pre_no_runner(self, mock_sudo_execute, mock_specrunner):
        mock_runner = MagicMock()
        mock_specrunner.return_value = mock_runner
        type(mock_specrunner).reboot_state = PropertyMock(return_value="/foo/bar")

        self.coordinator = Coordinator(self.testspec)
        self.coordinator.on_check_for_updates_pre("foo")
        self.coordinator.on_install_pre("foo")
        mock_runner.stop.assert_not_called()

    @patch("fiotest.main.SpecRunner")
    @patch("fiotest.host.sudo_execute", return_value=0)
    def test_coordinator_on_install_pre(self, mock_sudo_execute, mock_specrunner):
        mock_runner = MagicMock()
        mock_specrunner.return_value = mock_runner
        type(mock_specrunner).reboot_state = PropertyMock(return_value="/foo/bar")

        self.coordinator = Coordinator(self.testspec)
        self.coordinator.on_check_for_updates_pre("foo")
        self.coordinator.on_install_post("foo", "OK")
        mock_specrunner.assert_called_once_with(self.testspec)
        mock_runner.start.assert_called_once()
        self.coordinator.on_install_pre("foo")
        mock_runner.stop.assert_called()


class TestRunner(unittest.TestCase):
    def setUp(self):
        data = yaml.safe_load(SIMPLE_TEST_SPEC)
        self.testspec = TestSpec.parse_obj(data)

    @patch("fiotest.api.API.test_url", return_value="https://example.com/{FOO}")
    @patch("fiotest.runner.API.file_variables", return_value={"LMP_FACTORY": "factory", "CUSTOM_VERSION": 123, "LMP_MACHINE": "foo"})
    @patch("fiotest.api.DeviceGatewayClient")
    @patch("requests.get")
    @patch("subprocess.Popen")
    @patch("os.path.exists", return_value=True)
    def test_run(self, mock_path_exists, mock_popen, mock_requests_get, mock_gateway_client, mock_file_variables, mock_test_url):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_requests_get.return_value = mock_response
        specrunner = SpecRunner(self.testspec)
        specrunner.running = True  # run synchronously for testing
        specrunner.run()
        mock_requests_get.assert_called_with("https://example.com/factory/123/foo")
        mock_popen.assert_called()


if __name__ == '__main__':
    unittest.main()
