"""Global ARGS RFM/RIP Parser"""
from helpers.global_vars import root_dir


def get_tookit_args(get_parser):
    """ Get args toolkit """
    parser = get_parser()
    args = parser.parse_args()
    if not vars(args):
        parser.print_help()
        parser.exit(1)
    return args


def add_common_arguments(_parser):
    _parser.add_argument(
        "-c",
        "--config-dir",
        dest="configdir",
        default=f"{root_dir}/.config/",
        action="store",
        help="Chemin du repertoire config"
    )
    _parser.add_argument(
        "-e",
        "--extra-vars",
        type=str,
        action='append',
        default=[],
        help="Ajoute des variables supplémentaires"
    )
    _parser.add_argument(
        "-v",
        "--verbose",
        default=False,
        action="store_true",
        help="Mode verbeux d'ansible"
    )
    _parser.add_argument(
        "-p",
        "--prefix",
        default=None,
        required=True,
        help="Préfixe de la stack suivi du nom de domaine (ex: prefixip ou prefixcore1)"
    )

    _parser.add_argument(
        "-i",
        "--inventory",
        default=None,
        required=True,
        help="Chemin vers le fichier inventaire statique de la stack"
    )
