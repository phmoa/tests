""" Global utils Functions """
import subprocess as sb
import sys
import re

from helpers.global_vars import RFMBusinessDomains, environment, \
    root_dir, colors, RFMMiddlewares, RIPMiddlewares, CAPaths


common_services = ['sqlrfm', 'ebx', 'httpd', 'apacheds']
rfm_services = common_services
rip_services = common_services + ['confluent']
envs = ['DEV', 'REC', 'KAL', 'SYS', 'ROP']
common_security_zones = ['PXY', 'RFM', 'BIP']
common_middlewares = ['RFM', 'LDP', 'SQL']
middleware_service = {
    "apacheds": "apacheds",
    "httpd": "httpd",
    "postgresql": "sqlrfm",
    "ebx": "ebx",
    "mck": "confluent"
}


def get_default_middlewares(domain):
    """
    Récupère les middlewares

    Paramètres:
    ===========
        domain (str): rfm_stack

    variables locales:
    ==================
        middleware : Utilitaire d'itération
        middlewares (dict): Utilitaire qui stocke les middlewares

    Retour:
    =======
        result (dict) : { middleware (str): ("short_name" (str), "zone" (str), priorité (int)) }
    """
    result = {}
    middlewares = []
    if domain == RFMBusinessDomains.CORE1.value:
        middlewares = list(RFMMiddlewares)
    elif domain == RFMBusinessDomains.IP.value:
        middlewares = list(RIPMiddlewares)

    for middleware in middlewares:
        result[middleware.name] = middleware.value
    return result


def run_ansible_playbook(cmd):
    """
    Run ansible playbook
    """
    sb.run(cmd, text=True, env=environment, check=True)


def check_instance_compile_file(domain, env):
    """
    Check if instance_compile file exists
    """
    try:
        #
        with open(f"{root_dir}/.instances_compiled_files/" + domain + "/" +
                  env + "/.instances_compiled.yml", encoding="utf-8"):
            pass
    except FileNotFoundError:
        print(
            f"{colors['FAIL']}le fichier instances_compiled.yml est introuvable."
            f" Lancer la commande: python scripts/generer_instance_compile.py ")
        sys.exit(1)


def get_stet_ca_name(env):
    """
    Return STET ZAC CA name
    """
    if env.upper() in ['KAL', 'DEV', 'REC', 'SYS']:
        return CAPaths.ZNP_ZAC_STET_CA.value
    elif env.upper() in ['ROP']:
        return CAPaths.ZPR_ZAC_STET_CA.value
    else:
        raise ValueError(f"Unknow env {env.upper()}")
