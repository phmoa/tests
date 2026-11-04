""" RIPToolKit main class to manage ROP stack """

from helpers.rfm_manager import RFMToolKitManager
from helpers.global_vars import root_dir, colors, RFMBusinessDomains
from helpers.utils import run_ansible_playbook


class RIPToolKit(RFMToolKitManager):
    """
    RIPToolKit class to manage RIP stack
    """

    def __init__(self, args, rfm_business_domain):
        super().__init__(args, rfm_business_domain)
        if "app_version" in args:
            self.app_version = args.app_version

    def compile(self):
        """ Compile RIP stack command """

        if self.command == "install":
            self.install()

        if self.command == "middleware":
            if self.args.subcommand == "configure":
                self.configure()
            if self.args.subcommand == "install":
                self.install()
            if self.args.subcommand == "uninstall":
                self.uninstall()
            if self.args.subcommand == "status":
                self.command = "status"
                for middleware in self.args.middlewares_list:
                    self.app = middleware
                    self.systemctl()
            if self.args.subcommand == "stop":
                self.command = "stopped"
                for middleware in self.args.middlewares_list:
                    self.app = middleware
                    self.systemctl()
            if self.args.subcommand == "start":
                self.command = "started"
                for middleware in self.args.middlewares_list:
                    self.app = middleware
                    self.systemctl()
            if self.args.subcommand == "restart":
                self.command = "restarted"
                for middleware in self.args.middlewares_list:
                    self.app = middleware
                    self.systemctl()
            self.command = None

        self.handle_common_command()
