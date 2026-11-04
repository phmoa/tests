"""RFMToolKitManager manage commons attr and functions between RFM and IP"""
import os
import sys
import yaml
import hvac
import subprocess

from jinja2 import Template
from helpers.global_vars import root_dir, \
    RFMBusinessDomains, colors
from helpers.utils import run_ansible_playbook, \
    get_default_middlewares, middleware_service, rfm_services, rip_services, get_stet_ca_name


class RFMToolKitManager:
    """
    Cette class gerère les attr et les fonctions communs entre RFM et RIP
    """

    def __init__(self, args, rfm_business_domain):
        self.args = args
        self.business_domain = rfm_business_domain
        self.env = args.env.upper()
        self.command = args.command
        self.prefix = args.prefix
        self.configdir = args.configdir
        self.verbose = args.verbose
        self.extra_vars = args.extra_vars
        self.zone = args.zone
        self.middleware = args.middleware
        self.inventory = args.inventory
        if "app" in args:
            self.app = args.app

        if "dry_run" in args:
            self.dry_run = args.dry_run

        if "dry_run" in args:
            self.dry_run = args.dry_run

        if "reinstall" in args:
            self.reinstall = args.reinstall

        if rfm_business_domain == RFMBusinessDomains.CORE1.value:
            self.rfm_vault = "rfm"
        else:
            self.rfm_vault = "rip"

        if "app_version" in args:
            self.app_version = args.app_version

        # Check ca cert file
        self.ca_cert = get_stet_ca_name(args.env)
        if not os.path.exists(self.ca_cert):
            print(f"\n{colors['FAIL']}Le certificat CA {self.ca_cert} est requis{colors['ENDC']}")
            exit(1)

    def systemctl(self):
        """ Commande status """

        if self.app in 'all' or middleware_service[self.app] in rfm_services or middleware_service[self.app] in rip_services:

            if self.app != 'all':
                self.app = middleware_service[self.app]

            cmd = self.get_ansible_cmd_common_params() + [
                f"{root_dir}/ansible/playbooks/exploit/systemd.yml",
                "-e",
                "".join([f"tag_prefix=rfm_{self.env.lower()}_{self.prefix}",
                         f" app={self.app} env={self.env} command={self.command}"])
            ]
            run_ansible_playbook(cmd)
        else:
            raise ValueError(f"Unknow service {self.app}")

    def check(self):
        """ Check toolkit requirements """
        print(f"Checking {self.env} environment toolkit requirements")
        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/check/main.yml",
            "-e",
            f"tag_prefix={self.prefix} env={self.env}",
            "-e",
            "project=RFM"
        ]
        run_ansible_playbook(cmd)

    def deploy(self):
        """ Deploy EBX stack command """
        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/deploy/deploy-ebx.yml",
            "-e",
            "".join([f"zone=RFM middleware=RFM ",
                     f"ebx_version={self.app_version} ",
                     f"tag_prefix=rfm_{self.env.lower()}_{self.prefix} ",
                     f"env={self.env}"])
        ]
        run_ansible_playbook(cmd)

    def get_middlewares(self):
        """
        Récupère les middlewares depuis les arguments

        variables locales:
        ==================
            middlewares (dict): Utilitaire qui stocke les zones
            default_middlewares (dict) : Utilitaire qui stocke les zones par défauts
            i : Utilitaire d'itération

        Retour:
        =======
            middlewares (dict) : { middleware (str): ("short_name" (str), "zone" (str), priorité (int)) }
        """
        # Récupération des middlewares par défaut
        middlewares = {}
        default_middlewares = get_default_middlewares(self.business_domain)

        # Récupération des middlewares depuis les arguments
        try:
            for i in self.args.middlewares_list:
                if i == "ALL":
                    return default_middlewares
                if i not in list(default_middlewares.keys()):
                    messages = (
                        f"{colors['FAIL']}{i} n'est pas un middleware "
                        f"d'une stack RFM "
                        f"  ... {colors['ENDC']}\n"
                    )
                    print(messages)
                    sys.exit(1)
                else:
                    middlewares[i] = default_middlewares[i]
        except AttributeError as e:
            if e.args[0] == "'Namespace' object has no attribute 'middlewares_list'":
                return default_middlewares
            else:
                sys.exit(1)
        except TypeError as te:
            if te.args[0] == "'NoneType' object is not iterable":
                return default_middlewares
            else:
                sys.exit(1)
        return middlewares

    def filter_middlewares_by_zone(self, middlewares):
        result = {}
        try:
            for zone in self.args.zones_list:
                for key, value in middlewares.items():
                    if value[1] == zone.upper():
                        result[key] = value
            return result
        except AttributeError as e:
            if e.args[0] == "'Namespace' object has no attribute 'zones_list'":
                return middlewares
            else:
                sys.exit(1)
        except TypeError as te:
            if te.args[0] == "'NoneType' object is not iterable":
                return middlewares
            else:
                sys.exit(1)
        return middlewares

    def configure(self):
        """
        Configure les middlewares d'une stack selon l'ordre de priorité d'installation

        variables locales:
        ==================
            middlewares (dict): Utilitaire qui stocke les middlewares
            default_middlewares (dict) : Utilitaire qui stocke les middlewares par défauts
            middleware : Utilitaire d'itération
            cmd (str): commande pour ansible

        Retour:
        =======
            None
        """
        # Récupération des middlewares
        middlewares = self.get_middlewares()

        # Filtrage des middlewares par les zones
        middlewares = self.filter_middlewares_by_zone(middlewares)

        # La Configuration d'ebx se fait lors du deploy
        if "ebx" in list(middlewares.keys()):
            del middlewares["ebx"]

        # pour tous les élements de liste zm triée en fonction de la priorité
        for middleware in sorted(middlewares.items(), key=lambda z: z[1][2]):
            instance = middleware[1][0]
            zone = middleware[1][1]

            cmd = self.get_ansible_cmd_common_params() + [
                f"{root_dir}/ansible/playbooks/configure/{zone}_{instance}.yml",
                "-e",
                "".join([f"zone={zone} middleware={instance} ",
                         f"tag_prefix=rfm_{self.env.lower()}_{self.prefix} ",
                         f"env={self.env}"])
            ]
            run_ansible_playbook(cmd)

    def initvm(self):
        """
        Initialise les VM d'une stack

        Returns: None

        Raises: TypeError
        """
        # init vms
        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/provision/init_vm.yml",
            "-e",
            f"tag_prefix=rfm_{self.env.lower()}_{self.prefix} env={self.env}",
            "-t",
            "idm, createfs, firewalld"
        ]
        run_ansible_playbook(cmd)

    def install(self):
        """ Install les middlewares d'une stack """
        tag = []
        if "reinstall" in self.args:
            tag = [["--skip-tags", "reinstall"],
                   ["--tags", "all"]][self.reinstall]
        # Récupération des middlewares
        middlewares = self.get_middlewares()

        # Filtrage des middlewares par les zones
        middlewares = self.filter_middlewares_by_zone(middlewares)

        zone_middleware = ",".join(
            f"{value[1]}_{value[0]}" for value in middlewares.values())

        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/install/main.yml",
            "-e",
            "".join([f"zone_middleware={zone_middleware} ",
                     f"tag_prefix=rfm_{self.env.lower()}_{self.prefix} ",
                     f"env={self.env}"])
        ] + tag
        run_ansible_playbook(cmd)

    def uninstall(self):
        """ Uninstall les middlewares d'une stack """
        middlewares = self.get_middlewares()

        # Filtrage des middlewares par les zones
        middlewares = self.filter_middlewares_by_zone(middlewares)

        zone_middleware = ",".join(
            f"{value[1]}_{value[0]}" for value in middlewares.values())

        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/uninstall/main.yml",
            "-e",
            "".join([f"zone_middleware={zone_middleware} ",
                     f"tag_prefix=rfm_{self.env.lower()}_{self.prefix} ",
                     f"env={self.env}"])
        ]
        run_ansible_playbook(cmd)

    def validate(self):
        """Validate stack sate using Ansible assert modules"""

        cmd = self.get_ansible_cmd_common_params() + [
            f"{root_dir}/ansible/playbooks/validate/main.yml",
            "-e",
            "".join([f"tag_prefix=rfm_{self.env.lower()}_{self.prefix}",
                     f" env={self.env}"])
        ]
        middlewares = self.get_middlewares()
        for value in middlewares.values():
            zone_middleware = f"&z{value[1]}:&{value[0]}"
            cmd.append(
                f"-e middleware={value[3]} zone_middleware={zone_middleware}")
            run_ansible_playbook(cmd)

    def handle_common_command(self):
        """ Handle common command """
        if self.command in ['started', 'stopped', 'restarted', 'status']:
            self.systemctl()

        if self.command == "initvm":
            self.initvm()

        if self.command == "uninstall":
            self.uninstall()

        if self.command == "validate":
            self.validate()

        if self.command == "deploy":
            self.deploy()

    def get_ansible_cmd_common_params(self):
        """ Get ansible command common params """
        # Check for the --docker argument or DOCKER_MODE env variable
        is_docker_mode = getattr(self.args, 'docker', False) or os.environ.get('DOCKER_MODE', '').lower() == 'true' or os.environ.get('docker_mode', '').lower() == 'true'

        if is_docker_mode:
            ansible_executable = "ansible-playbook"
        else:
            ansible_executable = f"{root_dir}/.env/bin/ansible-playbook"

        cmd_ansible = [
            ansible_executable,
            "-i",
            f"{self.inventory}",
            "-e",
            f"ca_cert={self.ca_cert}",
            "-e",
            f"root_dir={root_dir} config_dir={os.path.realpath(self.configdir)} "
            f"business_domain={self.business_domain} rfm_vault={self.rfm_vault}"
        ]
        # si args.verbose alors -v
        verbose = [[], ["-v"]][self.verbose]
        extra_vars = [[], ["-e", ' '.join(self.extra_vars)]][bool(self.extra_vars)]
        limit = []
        # Add ansible native parameter --limit
        if self.zone is not None and self.middleware is not None:
            limit += ["--limit", f"z{self.zone}:&{self.middleware}"]
        elif self.zone is not None:
            limit += ["--limit", f"z{self.zone}"]
        elif self.middleware is not None:
            limit += ["--limit", f"{self.middleware}"]
        return cmd_ansible + limit + verbose + extra_vars

    def create_template(self):
        """ Générer les templates """
        with open(f"{self.configdir}/sizing/{self.env}/middlewares.yml", "r",
                  encoding="utf-8") as fsizemdl, \
                open(f"{self.configdir}/sizing/{self.env}/instances-{self.business_domain}.yml", "r",
                     encoding="utf-8") as fsizeins, \
                open(f"{self.configdir}/infra/{self.env}/main.yml", "r",
                     encoding="utf-8") as finfra, \
                open(f"{root_dir}/.instances_compiled_files/{self.business_domain}/{self.env}/.instances_compiled.yml", "w", encoding="utf-8") as cfile, \
                open(f"{root_dir}/ansible/ansible.cfg.tpl", "r", encoding="utf-8") as fanstpl, \
                open(f"{root_dir}/ansible/ansible.cfg", "w", encoding="utf-8") as fans:
            # ces 2 lignes servent à convertir les anchors jinja
            NoaliasDumper = yaml.dumper.SafeDumper
            NoaliasDumper.ignore_aliases = lambda self, data: True

            config = yaml.load(fsizemdl.read() + fsizeins.read(),
                               Loader=yaml.FullLoader)["INSTANCES"]
            # copy conf to instance_compiled so people can have a better look at it
            cfile.write(yaml.dump(config, Dumper=NoaliasDumper))

            infra = yaml.load(finfra.read(), Loader=yaml.FullLoader)

            vault_token = os.environ.get('VAULT_TOKEN')

            if vault_token is None:
                raise RuntimeError("VAULT_TOKEN environment variable is missing.")

            client = hvac.Client(
                url=infra["vault"]["url"],
                token=vault_token,
                verify=f"{self.ca_cert}"
            )

            # ansible.cfg config template
            template = Template(fanstpl.read())
            fans.write(
                template.render(
                    rootdir=root_dir,
                    username="stetuser",
                    password=client.secrets.kv.v2.read_secret_version(
                        path=self.env.lower() + "/stetuser", mount_point=f'kv/{self.rfm_vault}'
                    )["data"]["data"]["password"],
                )
            )
