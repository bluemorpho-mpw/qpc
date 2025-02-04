"""Test the CLI module."""
import os
import sys
import unittest
from argparse import ArgumentParser, Namespace
from io import StringIO

import requests
import requests_mock

from qpc import messages
from qpc.cli import CLI
from qpc.cred import (
    CREDENTIAL_URI,
    NETWORK_CRED_TYPE,
    SATELLITE_CRED_TYPE,
    VCENTER_CRED_TYPE,
)
from qpc.cred.edit import CredEditCommand
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import get_server_location, write_server_config

TMP_KEY = "/tmp/testkey"


class CredentialEditCliTests(unittest.TestCase):
    """Class for testing the credential edit commands for qpc."""

    def _init_command(self):
        """Return command with argument parser properly initialized."""
        argument_parser = ArgumentParser()
        subparser = argument_parser.add_subparsers(dest="subcommand")
        return CredEditCommand(subparser)

    def setUp(self):
        """Create test setup."""
        # different from most other test cases where command is initialized once per
        # class, this one requires to be initialized for each test method because
        # SourceEditCommand instance modifies req_path on the fly. This seems to be a
        # code smell to me, but I'm choosing to ignore it for now
        self.command = self._init_command()
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()
        if os.path.isfile(TMP_KEY):
            os.remove(TMP_KEY)
        with open(TMP_KEY, "w", encoding="utf-8") as test_sshkey:
            test_sshkey.write("fake ssh keyfile.")

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        sys.stderr = self.orig_stderr
        if os.path.isfile(TMP_KEY):
            os.remove(TMP_KEY)

    def test_edit_req_args_err(self):
        """Testing the credential edit command required flags."""
        cred_out = StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(cred_out):
                sys.argv = ["/bin/qpc", "credential", "edit", "--name", "credential1"]
                CLI().main()

    def test_edit_bad_key(self):
        """Testing the credential edit command.

        When providing an invalid path for the sshkeyfile.
        """
        cred_out = StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(cred_out):
                sys.argv = [
                    "/bin/qpc",
                    "credential",
                    "edit",
                    "--name",
                    "cred1",
                    "--sshkeyfile",
                    "bad_path",
                ]
                CLI().main()

    def test_edit_cred_none(self):
        """Testing the edit credential command for non-existing credential."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI + "?name=cred_none"
        with requests_mock.Mocker() as mocker:
            mocker.get(url, status_code=200, json={"count": 0})
            args = Namespace(
                name="cred_none",
                username="root",
                filename=TMP_KEY,
                password=None,
                become_password=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_edit_cred_ssl_err(self):
        """Testing the edit credential command with a connection error."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.SSLError)
            args = Namespace(
                name="credential1",
                username="root",
                filename=TMP_KEY,
                password=None,
                become_password=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_edit_cred_conn_err(self):
        """Testing the edit credential command with a connection error."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(url, exc=requests.exceptions.ConnectTimeout)
            args = Namespace(
                name="credential1",
                username="root",
                filename=TMP_KEY,
                password=None,
                become_password=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_edit_host_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": NETWORK_CRED_TYPE,
                "username": "root",
                "sshkeyfile": "/foo/bar",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(
                name="cred1",
                username="root",
                filename=TMP_KEY,
                sshkeyfile="/woot/ness",
                become_password=None,
                ssh_passphrase=None,
            )
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])

    def test_partial_edit_host_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": NETWORK_CRED_TYPE,
                "username": "root",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(
                name="cred1",
                username="root",
                filename=TMP_KEY,
                password=None,
                become_password=None,
                ssh_passphrase=None,
            )
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])

    def test_edit_vcenter_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": VCENTER_CRED_TYPE,
                "username": "root",
                "password": "********",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(name="cred1", username="root", password=None)
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])

    def test_partial_edit_vcenter_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": VCENTER_CRED_TYPE,
                "password": "********",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(name="cred1", username="root", password=None)
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])

    def test_edit_cred_get_error(self):
        """Testing the edit credential command server error occurs."""
        cred_out = StringIO()
        url_get = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=500, json=None)
            args = Namespace(
                name="cred1",
                username="root",
                filename=TMP_KEY,
                password=None,
                become_password=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_edit_sat_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": SATELLITE_CRED_TYPE,
                "username": "root",
                "password": "********",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(name="cred1", username="root", password=None)
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])

    def test_partial_edit_sat_cred(self):
        """Testing the edit credential command successfully."""
        url_get = get_server_location() + CREDENTIAL_URI
        url_patch = get_server_location() + CREDENTIAL_URI + "1/"
        results = [
            {
                "id": 1,
                "name": "cred1",
                "cred_type": SATELLITE_CRED_TYPE,
                "password": "********",
            }
        ]
        data = {"count": 1, "results": results}
        with requests_mock.Mocker() as mocker:
            mocker.get(url_get, status_code=200, json=data)
            mocker.patch(url_patch, status_code=200)
            args = Namespace(name="cred1", username="root", password=None)
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_UPDATED % "cred1"
                self.assertIn(expected_message, log.output[-1])
