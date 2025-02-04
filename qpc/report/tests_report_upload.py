"""Test the CLI module."""

import os
import sys
import unittest
from argparse import ArgumentParser, Namespace

import requests_mock

from qpc import messages
from qpc.release import PKG_NAME
from qpc.report import ASYNC_MERGE_URI
from qpc.report.upload import ReportUploadCommand
from qpc.tests_utilities import DEFAULT_CONFIG, HushUpStderr
from qpc.utils import get_server_location, write_server_config

TMP_BADDETAILS1 = (
    "/tmp/testbaddetailsreport_source.json",
    '{"id": 4,"bsources":[{"facts": ["A"],"server_id": "8"}]}',
)
TMP_GOODDETAILS = (
    "/tmp/testgooddetailsreport.json",
    '{"id": 4,"sources":[{"facts": ["A"],"server_id": "8"}]}',
)
NONEXIST_FILE = "/tmp/does/not/exist/bad.json"
JSON_FILES_LIST = [TMP_BADDETAILS1, TMP_GOODDETAILS]


class ReportUploadTests(unittest.TestCase):
    """Class for testing the scan show commands for qpc."""

    @classmethod
    def setUpClass(cls):
        """Set up test case."""
        argument_parser = ArgumentParser()
        subparser = argument_parser.add_subparsers(dest="subcommand")
        cls.command = ReportUploadCommand(subparser)

    def setUp(self):
        """Create test setup."""
        write_server_config(DEFAULT_CONFIG)
        # Temporarily disable stderr for these tests, CLI errors clutter up
        # nosetests command.
        self.orig_stderr = sys.stderr
        sys.stderr = HushUpStderr()
        for file in JSON_FILES_LIST:
            if os.path.isfile(file[0]):
                os.remove(file[0])
            with open(file[0], "w", encoding="utf-8") as test_file:
                test_file.write(file[1])

    def tearDown(self):
        """Remove test setup."""
        # Restore stderr
        for file in JSON_FILES_LIST:
            if os.path.isfile(file[0]):
                os.remove(file[0])
        sys.stderr = self.orig_stderr

    def test_upload_good_details_report(self):
        """Test uploading a good details report."""
        put_report_data = {"id": 1}
        put_merge_url = get_server_location() + ASYNC_MERGE_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(put_merge_url, status_code=201, json=put_report_data)

            args = Namespace(json_file=TMP_GOODDETAILS[0])
            with self.assertLogs(level="INFO") as log:
                self.command.main(args)
                expected_message = messages.REPORT_SUCCESSFULLY_UPLOADED % {
                    "id": "1",
                    "pkg_name": PKG_NAME,
                }

                self.assertIn(expected_message, log.output[-1])

    def test_upload_bad_details_report(self):
        """Test uploading a bad details report."""
        put_report_data = {"id": 1}
        put_merge_url = get_server_location() + ASYNC_MERGE_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(put_merge_url, status_code=201, json=put_report_data)

            args = Namespace(json_file=TMP_BADDETAILS1[0])
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    self.command.main(args)
                err_msg = messages.REPORT_UPLOAD_FILE_INVALID_JSON % (
                    TMP_BADDETAILS1[0]
                )
                self.assertIn(err_msg, log.output[-1])

    def test_upload_bad_details_report_no_fingerprints(self):
        """Test uploading a details report that produces no fingerprints."""
        put_report_data = {
            "error": "FAILED to create report id=23 - produced no valid fingerprints"
        }
        put_merge_url = get_server_location() + ASYNC_MERGE_URI
        with requests_mock.Mocker() as mocker:
            mocker.post(put_merge_url, status_code=400, json=put_report_data)

            args = Namespace(json_file=TMP_GOODDETAILS[0])
            with self.assertLogs(level="ERROR") as log:
                with self.assertRaises(SystemExit):
                    self.command.main(args)
                err_msg = messages.REPORT_FAILED_TO_UPLOADED % (
                    put_report_data.get("error")
                )
                self.assertIn(err_msg, log.output[-1])
