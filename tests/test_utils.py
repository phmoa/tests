"""Caractérisation : fonctions utilitaires (sans bac à sable)."""
import pytest

from helpers import utils
from helpers.global_vars import CAPaths


def test_middlewares_par_defaut_ip():
    assert utils.get_default_middlewares("ip") == {
        "apacheds": ("LDP", "BIP", 0, "LDP"),
        "httpd": ("RFM", "PXY", 0, "PXY"),
        "postgresql": ("SQL", "RFM", 0, "SQL"),
        "ebx": ("RFM", "RFM", 1, "EBX"),
        "mck": ("MCK", "RFM", 0, "MCK"),
    }


def test_middlewares_par_defaut_core1_sans_mck():
    assert list(utils.get_default_middlewares("core1")) == [
        "apacheds", "httpd", "postgresql", "ebx"]


def test_domaine_inconnu_renvoie_un_dictionnaire_vide():
    """BUG ACTUEL : aucune erreur pour un domaine inconnu."""
    assert utils.get_default_middlewares("sabr") == {}


@pytest.mark.parametrize("env", ["dev", "REC", "kal", "sys"])
def test_ca_hors_prod(env):
    assert utils.get_stet_ca_name(env) == CAPaths.ZNP_ZAC_STET_CA.value


def test_ca_prod():
    assert utils.get_stet_ca_name("rop") == CAPaths.ZPR_ZAC_STET_CA.value


def test_ca_env_inconnu():
    with pytest.raises(ValueError, match="Unknow env PRD"):
        utils.get_stet_ca_name("prd")


def test_rfm_services_est_un_alias_de_common_services():
    """PIÈGE ACTUEL : modifier l'une des listes modifie l'autre."""
    assert utils.rfm_services is utils.common_services


def test_chaque_middleware_a_un_service():
    assert set(utils.get_default_middlewares("ip")) == set(utils.middleware_service)
