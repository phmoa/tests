"""ARGS RIP Parser"""
# Imports de packages de la bibliothèque standard
import argparse

# Imports locaux
from helpers.global_args_parser import add_common_arguments
from helpers.utils import rip_services
from helpers.utils import common_security_zones, common_middlewares

CONFLUENCE = ("\thttps://atlassian.aws.projets.stet/confluence/pages/viewpage.action"
              "?spaceKey=MOE2020&title=RIP+Toolkit+-+Manuel+d%27utilisation")


def get_rip_parser():
    """Create RIP parser"""
    parser = argparse.ArgumentParser(prog="toolkit")
    parser.formatter_class = argparse.RawDescriptionHelpFormatter
    parser.epilog = (
        "Examples :\n\n"
        "    Pour plus de details sur le sous commandes toolkit  (initvm|middleware|deploy| ...)\n"
        "\tbin/toolkit sous-commande -h\n"
        "\tbin/toolkit initvm -p <nom de stack> --env <env> --inventory ansible/inventory/inventory.yml\n"
        "    Pour plus d'aide sur l'utilisation de rip-toolkit, consulter la page confluence:\n"
        + CONFLUENCE
    )

    sub_parser = parser.add_subparsers(help="***Sous commandes toolkit***")

    # initvm
    p_initvm = sub_parser.add_parser(
        "initvm",
        help="Initialiser des VMs",
        epilog=(
            "Examples :\n\n"
            "    Initialiser des VM\n"
            "\tbin/toolkit initvm -p <nom de stack> --env <env> --inventory ansible/inventory/inventory.yml\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_initvm, dest="initvm")

    # MIDDLEWARE
    p_middleware = sub_parser.add_parser(
        "middleware",
        help="Agir sur des middlewares d'une stack",
        epilog=(
            "Examples :\n\n"
            "    Installer des middelewares EBX, HTTPD, APACHEDS, POSTGRESQL, MCK \n"
            "\tbin/toolkit middleware install -p <nom de stack> --env <env> --inventory ansible/inventory/inventory.yml\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    subparser_middleware = p_middleware.add_subparsers(
        help="***middleware sub commandes***", dest="subcommand")

    # MIDDLEWARE CONFIGURE
    p_configure = subparser_middleware.add_parser(
        "configure",
        help="Configurer des middlewares",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_configure, dest="middleware")

    # MIDDLEWARE INSTALL
    p_install = subparser_middleware.add_parser(
        "install",
        help="Installer des middlewares",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_install, dest="middleware")

    # UNINSTALL MIDDLEWARE
    p_uninstall = subparser_middleware.add_parser(
        "uninstall",
        help="Désinstaller des middlewares",
        epilog=(
            "Examples :\n\n"
            "    Désinstaller multiple middlewares\n"
            "\tbin/toolkit middleware uninstall -p mystackip --env dev --inventory ansible/inventory/inventory.yml"
            " --middlewares-list {httpd,ebx,postgresql}\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_uninstall, dest="middleware")

    # DEPLOY
    p_deploy = sub_parser.add_parser(
        "deploy",
        help="Déployer d'application EBX ",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_deploy, dest="deploy")

    #
    # STATUS
    p_status = subparser_middleware.add_parser(
        "status",
        help="Vérifier l'état des middlewares",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_status, dest="middleware")

    #
    # START
    p_start = subparser_middleware.add_parser(
        "start",
        help="Démarrer des middlewares",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_start, dest="middleware")

    # STOP
    p_stop = subparser_middleware.add_parser(
        "stop",
        help="Stopper de middlewares",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_stop, dest="middleware")

    # RESTARTED
    p_restart = subparser_middleware.add_parser(
        "restart",
        help="Restart des middlewares (stop puis start)",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_restart, dest="middleware")

    # Validate stack
    p_validate = sub_parser.add_parser(
        "validate",
        help="Valider l'état d'une stack",
        epilog="Examples :\n\n",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_rip_arguments(p_validate, dest="validate")
    return parser


def _add_rip_arguments(_parser, dest):
    """ Add RIP ARGS options """
    _parser.add_argument('--docker',
                         action='store_true',
                         help='Skip virtualenv, use system packages (for Docker)')
    if dest == "deploy":
        _parser.add_argument(
            "--app-version",
            action="store",
            required=True,
            help="Déployer l'application EBX ",

        )

    if dest in ["middleware"]:
        _parser.add_argument(
            "--middlewares-list",
            help="List of middlewares",
            choices=["apacheds", "httpd", "postgresql", "ebx", "mck"],
            default=["apacheds", "httpd", "postgresql", "ebx", "mck"],
            nargs="+",
        )
        _parser.add_argument(
            "--zones-list",
            help="List of zones",
            choices=["bip", "pxy", "rfm"],
            default=["bip", "pxy", "rfm"],
            nargs="+",
        )
    add_common_arguments(_parser)

    _parser.add_argument(
        "--env",
        choices=["dev", "rec", "kal", "rop", "sys"],
        help="Environnement de stack",
        required=True,
        type=str.lower
    )
    _parser.add_argument(
        "--zone",
        choices=common_security_zones + ['PUB'],
        help="Limite l'action à une zone de sécurité"
    )
    _parser.add_argument(
        "--middleware",
        choices=common_middlewares + ['DWL', 'MCK'],
        help="Limite l'action à un middleware"
    )

    _parser.set_defaults(command=dest)
