"""QPC Command Line Interface."""

import sys
from argparse import ArgumentParser

from qpc import cred, insights, messages, report, scan, server, source
from qpc.cred.commands import (
    CredAddCommand,
    CredClearCommand,
    CredEditCommand,
    CredListCommand,
    CredShowCommand,
)
from qpc.insights.commands import (
    InsightsAddLoginCommand,
    InsightsConfigureCommand,
    InsightsPublishCommand,
)
from qpc.release import PKG_NAME, VERSION
from qpc.report.commands import (
    ReportDeploymentsCommand,
    ReportDetailsCommand,
    ReportDownloadCommand,
    ReportInsightsCommand,
    ReportMergeCommand,
    ReportMergeStatusCommand,
    ReportUploadCommand,
)
from qpc.scan.commands import (
    ScanAddCommand,
    ScanCancelCommand,
    ScanClearCommand,
    ScanEditCommand,
    ScanJobCommand,
    ScanListCommand,
    ScanPauseCommand,
    ScanRestartCommand,
    ScanShowCommand,
    ScanStartCommand,
)
from qpc.server.commands import (
    ConfigureHostCommand,
    LoginHostCommand,
    LogoutHostCommand,
    ServerStatusCommand,
)
from qpc.source.commands import (
    SourceAddCommand,
    SourceClearCommand,
    SourceEditCommand,
    SourceListCommand,
    SourceShowCommand,
)
from qpc.translation import _
from qpc.utils import (
    ensure_config_dir_exists,
    ensure_data_dir_exists,
    get_server_location,
    logger,
    read_client_token,
    read_require_auth,
    setup_logging,
)


class CLI:
    """Defines the CLI class.

    Class responsible for displaying usage or matching inputs
    to the valid set of commands supported by qpc.
    """

    def __init__(self, name="cli", usage=None, shortdesc=None, description=None):
        """Create main command line handler."""
        self.shortdesc = shortdesc
        if shortdesc is not None and description is None:
            description = shortdesc
        self.parser = ArgumentParser(usage=usage, description=description)
        self.parser.add_argument("--version", action="version", version=VERSION)
        self.parser.add_argument(
            "-v",
            dest="verbosity",
            action="count",
            default=0,
            help=_(messages.VERBOSITY_HELP),
        )
        self.subparsers = self.parser.add_subparsers(dest="subcommand")
        self.name = name
        self.args = None
        self.subcommands = {}
        self._add_subcommand(
            server.SUBCOMMAND,
            [
                ConfigureHostCommand,
                LoginHostCommand,
                LogoutHostCommand,
                ServerStatusCommand,
            ],
        )
        self._add_subcommand(
            cred.SUBCOMMAND,
            [
                CredAddCommand,
                CredListCommand,
                CredEditCommand,
                CredShowCommand,
                CredClearCommand,
            ],
        )
        self._add_subcommand(
            source.SUBCOMMAND,
            [
                SourceAddCommand,
                SourceListCommand,
                SourceShowCommand,
                SourceClearCommand,
                SourceEditCommand,
            ],
        )

        self._add_subcommand(
            scan.SUBCOMMAND,
            [
                ScanAddCommand,
                ScanStartCommand,
                ScanListCommand,
                ScanShowCommand,
                ScanPauseCommand,
                ScanCancelCommand,
                ScanRestartCommand,
                ScanEditCommand,
                ScanClearCommand,
                ScanJobCommand,
            ],
        )
        self._add_subcommand(
            report.SUBCOMMAND,
            [
                ReportDeploymentsCommand,
                ReportDetailsCommand,
                ReportInsightsCommand,
                ReportDownloadCommand,
                ReportMergeCommand,
                ReportMergeStatusCommand,
                ReportUploadCommand,
            ],
        )
        self._add_subcommand(
            insights.SUBCOMMAND,
            [
                InsightsConfigureCommand,
                InsightsAddLoginCommand,
                InsightsPublishCommand,
            ],
        )

        ensure_data_dir_exists()
        ensure_config_dir_exists()

    def _add_subcommand(self, subcommand, actions):
        subcommand_parser = self.subparsers.add_parser(subcommand)
        action_subparsers = subcommand_parser.add_subparsers(dest="action")
        self.subcommands[subcommand] = {}
        for action in actions:
            action_inst = action(action_subparsers)
            action_dic = self.subcommands[action.SUBCOMMAND]
            action_dic[action.ACTION] = action_inst

    def main(self):
        """Execute of subcommand operation.

        Method determine whether to display usage or pass input
        to find the best command match. If no match is found the
        usage is displayed
        """
        self.args = self.parser.parse_args()
        setup_logging(self.args.verbosity)
        is_server_cmd = self.args.subcommand == server.SUBCOMMAND
        is_server_logout = is_server_cmd and self.args.action == server.LOGOUT
        is_server_config = is_server_cmd and self.args.action == server.CONFIG

        if not is_server_config:
            # Before attempting to run command, check server location
            server_location = get_server_location()
            if server_location is None or server_location == "":
                logger.error(_(messages.SERVER_CONFIG_REQUIRED), PKG_NAME)
                sys.exit(1)

        if read_require_auth():
            if (not is_server_cmd or is_server_logout) and not read_client_token():
                logger.error(_(messages.SERVER_LOGIN_REQUIRED), PKG_NAME)
                sys.exit(1)

        if self.args.subcommand in self.subcommands:
            subcommand = self.subcommands[self.args.subcommand]
            if self.args.action in subcommand:
                action = subcommand[self.args.action]
                action.main(self.args)
            else:
                self.parser.print_help()
        else:
            self.parser.print_help()
