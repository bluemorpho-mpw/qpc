"""Test the CLI module."""

import os
import sys
import unittest
from argparse import ArgumentParser, Namespace  # noqa: I100
from io import StringIO
from unittest.mock import patch

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
from qpc.cred.add import CredAddCommand
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr, redirect_stdout
from qpc.utils import get_server_location, write_server_config

TMP_KEY = "/tmp/testkey"


class CredentialAddCliTests(unittest.TestCase):
    """Class for testing the credential add commands for qpc."""

    @classmethod
    def setUpClass(cls):
        """Set up test case."""
        argument_parser = ArgumentParser()
        subparser = argument_parser.add_subparsers(dest="subcommand")
        cls.command = CredAddCommand(subparser)

    def setUp(self):
        """Create test setup."""
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

    def test_add_req_args_err(self):
        """Testing the add credential command required flags."""
        with self.assertRaises(SystemExit):
            sys.argv = ["/bin/qpc", "credential", "add", "--name", "credential1"]
            CLI().main()

    def test_add_no_type(self):
        """Testing the add credential without type flag."""
        with self.assertRaises(SystemExit):
            sys.argv = [
                "/bin/qpc",
                "credential",
                "add",
                "--name",
                "credential1",
                "--username",
                "foo",
                "--password",
            ]
            CLI().main()

    def test_add_bad_key(self):
        """Testing the add credential command.

        When providing an invalid path for the sshkeyfile.
        """
        cred_out = StringIO()
        with self.assertRaises(SystemExit):
            with redirect_stdout(cred_out):
                sys.argv = [
                    "/bin/qpc",
                    "credential",
                    "add",
                    "--name",
                    "credential1",
                    "--username",
                    "root",
                    "--sshkeyfile",
                    "bad_path",
                ]
                CLI().main()

    def test_add_cred_name_dup(self):
        """Testing the add credential command duplicate name."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        error = {"name": ["credential with this name already exists."]}
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=400, json=error)
            args = Namespace(
                name="cred_dup",
                username="root",
                type=NETWORK_CRED_TYPE,
                filename=TMP_KEY,
                password=None,
                become_password=None,
                ssh_passphrase=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_add_cred_ssl_err(self):
        """Testing the add credential command with a connection error."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, exc=requests.exceptions.SSLError)
            args = Namespace(
                name="credential1",
                username="root",
                type=NETWORK_CRED_TYPE,
                filename=TMP_KEY,
                password=None,
                become_password=None,
                ssh_passphrase=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_add_cred_conn_err(self):
        """Testing the add credential command with a connection error."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, exc=requests.exceptions.ConnectTimeout)
            args = Namespace(
                name="credential1",
                username="root",
                type=NETWORK_CRED_TYPE,
                filename=TMP_KEY,
                password=None,
                become_password=None,
                ssh_passphrase=None,
            )
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    def test_add_host_cred(self):
        """Testing the add host cred command successfully."""
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=201)
            args = Namespace(
                name="credential1",
                username="root",
                type=NETWORK_CRED_TYPE,
                filename=TMP_KEY,
                password=None,
                ssh_passphrase=None,
                become_method=None,
                become_user=None,
                become_password=None,
            )
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_ADDED % "credential1"
                self.assertIn(expected_message, log.output[-1])

    def test_add_host_cred_with_become(self):
        """Testing the add host cred command successfully."""
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=201)
            args = Namespace(
                name="credential1",
                username="root",
                type=NETWORK_CRED_TYPE,
                filename=TMP_KEY,
                password=None,
                ssh_passphrase=None,
                become_method="sudo",
                become_user="root",
                become_password=None,
            )
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_ADDED % "credential1"
                self.assertIn(expected_message, log.output[-1])

    @patch("getpass._raw_input")
    def test_add_vcenter_cred(self, do_mock_raw_input):
        """Testing the add vcenter cred command successfully."""
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=201)
            args = Namespace(
                name="credential1",
                type=VCENTER_CRED_TYPE,
                username="root",
                password="sdf",
            )
            do_mock_raw_input.return_value = "abc"
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_ADDED % "credential1"
                self.assertIn(expected_message, log.output[-1])

    @patch("getpass._raw_input")
    def test_add_sat_cred(self, do_mock_raw_input):
        """Testing the add sat cred command successfully."""
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=201)
            args = Namespace(
                name="credential1",
                type=SATELLITE_CRED_TYPE,
                username="root",
                password="sdf",
            )
            do_mock_raw_input.return_value = "abc"
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.CRED_ADDED % "credential1"
                self.assertIn(expected_message, log.output[-1])

    @patch("getpass._raw_input")
    def test_add_cred_401(self, do_mock_raw_input):
        """Testing the 401 error flow."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(url, status_code=401)
            args = Namespace(
                name="credential1",
                type=SATELLITE_CRED_TYPE,
                username="root",
                password="sdf",
            )
            do_mock_raw_input.return_value = "abc"
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)

    @patch("getpass._raw_input")
    def test_add_cred_expired(self, do_mock_raw_input):
        """Testing the token expired flow."""
        cred_out = StringIO()
        url = get_server_location() + CREDENTIAL_URI
        with requests_mock.Mocker() as mocker:
            expired = {"detail": "Token has expired"}
            mocker.post(url, status_code=400, json=expired)
            args = Namespace(
                name="credential1",
                type=SATELLITE_CRED_TYPE,
                username="root",
                password="sdf",
            )
            do_mock_raw_input.return_value = "abc"
            with self.assertRaises(SystemExit):
                with redirect_stdout(cred_out):
                    self.command.main(args)
