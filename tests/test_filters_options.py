"""Caractérisation : filtres (--middlewares-list, --zones-list, --zone, --middleware)
et options communes (-v, -e, --docker, -c)."""
import os

import pytest

from conftest import BASE, make_config_dir

TP = "tag_prefix=rfm_dev_stackip"


def zone_middleware(commands):
    """Extrait la valeur zone_middleware=... du dernier -e de la commande."""
    return commands[0][-1].split(" ")[0]


# --- filtrage en Python ----------------------------------------------------

@pytest.mark.parametrize("extra, expected", [
    ([], "zone_middleware=BIP_LDP,PXY_RFM,RFM_SQL,RFM_RFM,RFM_MCK"),
    (["--zones-list", "rfm"], "zone_middleware=RFM_SQL,RFM_RFM,RFM_MCK"),
    (["--zones-list", "pxy", "bip"], "zone_middleware=PXY_RFM,BIP_LDP"),
    (["--middlewares-list", "httpd", "ebx"], "zone_middleware=PXY_RFM,RFM_RFM"),
    (["--middlewares-list", "ebx", "httpd"], "zone_middleware=PXY_RFM,RFM_RFM"),
    (["--middlewares-list", "mck", "--zones-list", "rfm"], "zone_middleware=RFM_MCK"),
])
def test_install_filtrage(toolkit, extra, expected):
    assert zone_middleware(toolkit.run("middleware", "install", *BASE, *extra)) == expected


def test_install_filtre_sans_resultat_lance_quand_meme_ansible(toolkit):
    """BUG ACTUEL : aucun middleware retenu, Ansible est lancé avec une liste vide."""
    commands = toolkit.run("middleware", "install", *BASE,
                           "--middlewares-list", "httpd", "--zones-list", "rfm")
    assert commands[0][-1] == f"zone_middleware= {TP} env=DEV"


def test_configure_filtre_par_zone(toolkit):
    commands = toolkit.run("middleware", "configure", *BASE, "--zones-list", "rfm")
    assert [c[-3] for c in commands] == [
        toolkit.playbook("configure/RFM_SQL.yml"),
        toolkit.playbook("configure/RFM_MCK.yml"),
    ]


def test_status_ignore_zones_list(toolkit):
    """--zones-list n'a aucun effet sur status/start/stop/restart."""
    commands = toolkit.run("middleware", "status", *BASE, "--zones-list", "bip")
    assert len(commands) == 5


# --- filtrage par --limit Ansible -----------------------------------------

@pytest.mark.parametrize("extra, limit", [
    (["--zone", "PXY"], ["--limit", "zPXY"]),
    (["--middleware", "SQL"], ["--limit", "SQL"]),
    (["--zone", "RFM", "--middleware", "RFM"], ["--limit", "zRFM:&RFM"]),
])
def test_limit(toolkit, extra, limit):
    commands = toolkit.run("initvm", *BASE, *extra)
    assert commands[0][:len(toolkit.common()) + 2] == toolkit.common() + limit


def test_limit_se_combine_avec_le_filtrage_python(toolkit):
    commands = toolkit.run("middleware", "install", *BASE,
                           "--zone", "PXY", "--middlewares-list", "httpd")
    assert commands == [
        toolkit.common() + ["--limit", "zPXY"] + [
            toolkit.playbook("install/main.yml"),
            "-e", f"zone_middleware=PXY_RFM {TP} env=DEV",
        ],
    ]


# --- options communes ------------------------------------------------------

def test_verbose(toolkit):
    commands = toolkit.run("initvm", *BASE, "-v")
    assert commands[0][len(toolkit.common())] == "-v"


def test_extra_vars_regroupees_en_un_seul_e(toolkit):
    commands = toolkit.run("initvm", *BASE, "-e", "a=1", "-e", "b=2")
    n = len(toolkit.common())
    assert commands[0][n:n + 2] == ["-e", "a=1 b=2"]


def test_ordre_limit_verbose_extra_vars(toolkit):
    commands = toolkit.run("initvm", *BASE, "--zone", "BIP", "-v", "-e", "x=1")
    n = len(toolkit.common())
    assert commands[0][n:n + 5] == ["--limit", "zBIP", "-v", "-e", "x=1"]


def test_extra_vars_ne_s_accumulent_pas_entre_deux_lancements(toolkit):
    """Le parser est recréé à chaque lancement : default=[] ne fuit pas."""
    toolkit.run("initvm", *BASE, "-e", "a=1")
    toolkit.recorder.commands.clear()
    commands = toolkit.run("initvm", *BASE)
    assert commands[0] == toolkit.common() + [
        toolkit.playbook("provision/init_vm.yml"),
        "-e", f"{TP} env=DEV", "-t", "idm, createfs, firewalld",
    ]


def test_option_docker(toolkit):
    commands = toolkit.run("initvm", *BASE, "--docker")
    assert commands[0][0] == "ansible-playbook"


@pytest.mark.parametrize("var", ["DOCKER_MODE", "docker_mode"])
def test_variable_docker_mode(toolkit, var):
    toolkit.monkeypatch.setenv(var, "TRUE")
    commands = toolkit.run("initvm", *BASE)
    assert commands[0][0] == "ansible-playbook"


def test_config_dir_utilise_pour_sizing_mais_pas_pour_la_ca(toolkit, tmp_path):
    """BUG ACTUEL : --config-dir change le sizing, mais la CA reste celle par défaut."""
    other = make_config_dir(tmp_path / "autre-config")
    commands = toolkit.run("initvm", *BASE, "-c", str(other))
    assert commands[0][:len(toolkit.common())] == toolkit.common(
        ca=toolkit.znp, configdir=str(other))
    assert os.path.realpath(str(other)) in commands[0][6]
    assert str(other) not in commands[0][4]
