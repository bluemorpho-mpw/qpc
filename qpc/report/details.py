#!/usr/bin/env python
#
# Copyright (c) 2018 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 3 (GPLv3). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv3
# along with this software; if not, see
# https://www.gnu.org/licenses/gpl-3.0.txt.
#
"""ReportDetailsCommand is used to show details report."""

from __future__ import print_function

import sys
from logging import getLogger

from requests import codes

from qpc import messages, report, scan
from qpc.clicommand import CliCommand
from qpc.request import GET, request
from qpc.translation import _
from qpc.utils import (
    check_extension,
    extract_json_from_tar,
    validate_write_file,
    write_file,
)

log = getLogger("qpc")


# pylint: disable=too-few-public-methods
class ReportDetailsCommand(CliCommand):
    """Defines the report details command.

    This command is for showing the details report.
    """

    SUBCOMMAND = report.SUBCOMMAND
    ACTION = report.DETAILS

    def __init__(self, subparsers):
        """Create command."""
        # pylint: disable=no-member
        CliCommand.__init__(
            self,
            self.SUBCOMMAND,
            self.ACTION,
            subparsers.add_parser(self.ACTION),
            GET,
            report.REPORT_URI,
            [codes.ok],
        )
        id_group = self.parser.add_mutually_exclusive_group(required=True)
        id_group.add_argument(
            "--scan-job",
            dest="scan_job_id",
            metavar="SCAN_JOB_ID",
            help=_(messages.REPORT_SCAN_JOB_ID_HELP),
        )
        id_group.add_argument(
            "--report",
            dest="report_id",
            metavar="REPORT_ID",
            help=_(messages.REPORT_REPORT_ID_HELP),
        )

        group = self.parser.add_mutually_exclusive_group(required=True)
        group.add_argument(
            "--json",
            dest="output_json",
            action="store_true",
            help=_(messages.REPORT_OUTPUT_JSON_HELP),
        )
        group.add_argument(
            "--csv",
            dest="output_csv",
            action="store_true",
            help=_(messages.REPORT_OUTPUT_CSV_HELP),
        )

        self.parser.add_argument(
            "--output-file",
            dest="path",
            metavar="PATH",
            help=_(messages.REPORT_PATH_HELP),
            required=True,
        )
        self.parser.add_argument(
            "--mask",
            dest="mask",
            action="store_true",
            help=_(messages.REPORT_MASK_HELP),
            required=False,
        )
        self.report_id = None
        self.min_server_version = "0.9.2"

    def _validate_args(self):
        CliCommand._validate_args(self)
        extension = None
        if self.args.output_json:
            extension = ".json"
            self.req_headers = {"Accept": "application/json+gzip"}
        if self.args.output_csv:
            extension = ".csv"
            self.req_headers = {"Accept": "text/csv"}
        if self.args.mask:
            self.req_params = {"mask": True}
        if extension:
            check_extension(extension, self.args.path)
        try:
            validate_write_file(self.args.path, "output-file")
        except ValueError as error:
            print(error)
            sys.exit(1)

        if self.args.report_id is None:
            # Lookup scan job id
            response = request(
                parser=self.parser,
                method=GET,
                path=f"{scan.SCAN_JOB_URI}{self.args.scan_job_id}",
                payload=None,
            )
            if response.status_code == codes.ok:  # pylint: disable=no-member
                json_data = response.json()
                self.report_id = json_data.get("report_id")
                if self.report_id:
                    self.req_path = (
                        f"{self.req_path}{self.report_id}{report.DETAILS_PATH_SUFFIX}"
                    )
                else:
                    print(
                        _(
                            messages.REPORT_NO_DETAIL_REPORT_FOR_SJ
                            % self.args.scan_job_id
                        )
                    )
                    sys.exit(1)
            else:
                print(_(messages.REPORT_SJ_DOES_NOT_EXIST % self.args.scan_job_id))
                sys.exit(1)
        else:
            self.report_id = self.args.report_id
            self.req_path = (
                f"{self.req_path}{self.report_id}{report.DETAILS_PATH_SUFFIX}"
            )

    def _handle_response_success(self):
        file_content = None
        if self.args.output_json:
            file_content = extract_json_from_tar(self.response.content)
        else:
            file_content = self.response.text

        try:
            write_file(self.args.path, file_content)
            log.info(_(messages.REPORT_SUCCESSFULLY_WRITTEN))
        except EnvironmentError as err:
            err_msg = _(messages.WRITE_FILE_ERROR % (self.args.path, err))
            log.error(err_msg)
            sys.exit(1)

    def _handle_response_error(self):  # pylint: disable=arguments-differ
        if self.args.report_id is None:
            print(_(messages.REPORT_NO_DETAIL_REPORT_FOR_SJ % self.args.scan_job_id))
        else:
            print(
                _(messages.REPORT_NO_DETAIL_REPORT_FOR_REPORT_ID % self.args.report_id)
            )
        sys.exit(1)
