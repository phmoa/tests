""" Global utils var """
import os
from enum import Enum

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
config_dir = f'{root_dir}/.config'
colors = {
    "HEADER": "\033[95m",
    "OKBLUE": "\033[94m",
    "OKCYAN": "\033[96m",
    "OKYELLOW": "\033[1;33m",
    "OKGREEN": "\033[92m",
    "WARNING": "\033[93m",
    "FAIL": "\033[91m",
    "ENDC": "\033[0m",
    "BOLD": "\033[1m",
    "UNDERLINE": "\033[4m",
}

# dictionnaire contenant les variables ANSIBLE + variables environnement
environment = {
    **{
        "ANSIBLE_FORCE_COLOR": "True",
        "ANSIBLE_STDOUT_CALLBACK": "yaml",
        "ANSIBLE_CONFIG": f"{root_dir}/ansible/ansible.cfg",
        **{k: os.environ[k] for k in os.environ},
    }
}


class CAPaths(Enum):
    """Enum CA paths"""
    ZNP_ZAC_STET_CA = f"{config_dir}/certificates/ca/znp_zac_stet.crt"
    ZPR_ZAC_STET_CA = f"{config_dir}/certificates/ca/zpr_zac_stet.crt"


class RFMBusinessDomains(Enum):
    """Enum RFM business domains"""
    CORE1 = "core1"
    IP = "ip"


class RFMMiddlewares(Enum):
    """Enum Middlewares
        "middleware_name" = ("short_name", "zone", "priority", "other_name")
    """
    apacheds = ("LDP", "BIP", 0, "LDP")
    httpd = ("RFM", "PXY", 0, "PXY")
    postgresql = ("SQL", "RFM", 0, "SQL")
    ebx = ("RFM", "RFM", 1, "EBX")


class RIPMiddlewares(Enum):
    """Enum Middlewares
        "middleware_name" = ("short_name", "zone", "priority", "other_name")
    """
    apacheds = ("LDP", "BIP", 0, "LDP")
    httpd = ("RFM", "PXY", 0, "PXY")
    postgresql = ("SQL", "RFM", 0, "SQL")
    ebx = ("RFM", "RFM", 1, "EBX")
    mck = ("MCK", "RFM", 0, "MCK")
