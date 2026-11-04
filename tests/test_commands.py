"""Caractérisation : commandes Ansible produites par chaque commande du toolkit."""
import pytest

from conftest import BASE

TP = "tag_prefix=rfm_dev_stackip"
ALL_ZONE_MIDDLEWARES = "BIP_LDP,PXY_RFM,RFM_SQL,RFM_RFM,RFM_MCK"


# --- commandes de premier niveau -----------------------------------------

def test_initvm(toolkit):
    assert toolkit.run("initvm", *BASE) == [
        toolkit.common() + [
            toolkit.playbook("provision/init_vm.yml"),
            "-e", f"{TP} env=DEV",
            "-t", "idm, createfs, firewalld",
        ],
    ]


def test_deploy(toolkit):
    assert toolkit.run("deploy", *BASE, "--app-version", "4.7.3") == [
        toolkit.common() + [
            toolkit.playbook("deploy/deploy-ebx.yml"),
            "-e", f"zone=RFM middleware=RFM ebx_version=4.7.3 {TP} env=DEV",
        ],
    ]


def test_validate_lance_un_playbook_par_middleware_et_accumule_les_e(toolkit):
    """BUG ACTUEL : la commande grossit à chaque tour, et '-e' est collé à sa valeur."""
    commands = toolkit.run("validate", *BASE)

    base = toolkit.common() + [toolkit.playbook("validate/main.yml"), "-e", f"{TP} env=DEV"]
    extras = [
        "-e middleware=LDP zone_middleware=&zBIP:&LDP",
        "-e middleware=PXY zone_middleware=&zPXY:&RFM",
        "-e middleware=SQL zone_middleware=&zRFM:&SQL",
        "-e middleware=EBX zone_middleware=&zRFM:&RFM",
        "-e middleware=MCK zone_middleware=&zRFM:&MCK",
    ]
    assert commands == [base + extras[: i + 1] for i in range(len(extras))]


# --- middleware install / uninstall / configure ---------------------------

def test_middleware_install_par_defaut(toolkit):
    assert toolkit.run("middleware", "install", *BASE) == [
        toolkit.common() + [
            toolkit.playbook("install/main.yml"),
            "-e", f"zone_middleware={ALL_ZONE_MIDDLEWARES} {TP} env=DEV",
        ],
    ]


def test_middleware_uninstall_par_defaut(toolkit):
    assert toolkit.run("middleware", "uninstall", *BASE) == [
        toolkit.common() + [
            toolkit.playbook("uninstall/main.yml"),
            "-e", f"zone_middleware={ALL_ZONE_MIDDLEWARES} {TP} env=DEV",
        ],
    ]


def test_middleware_configure_par_defaut_sans_ebx_par_priorite(toolkit):
    """ebx est retiré (configuré au deploy) ; un playbook par zone_instance."""
    expected = []
    for zone, instance in [("BIP", "LDP"), ("PXY", "RFM"), ("RFM", "SQL"), ("RFM", "MCK")]:
        expected.append(toolkit.common() + [
            toolkit.playbook(f"configure/{zone}_{instance}.yml"),
            "-e", f"zone={zone} middleware={instance} {TP} env=DEV",
        ])
    assert toolkit.run("middleware", "configure", *BASE) == expected


def test_middleware_configure_trie_par_priorite(toolkit):
    """Avec le catalogue actuel, seul ebx a une priorité non nulle, et il est retiré :
    le tri n'a donc aucun effet visible. Ce test le fige avec des priorités distinctes."""
    from helpers import rfm_manager
    catalog = {
        "postgresql": ("SQL", "RFM", 2, "SQL"),
        "apacheds": ("LDP", "BIP", 0, "LDP"),
        "httpd": ("RFM", "PXY", 1, "PXY"),
    }
    toolkit.monkeypatch.setattr(rfm_manager, "get_default_middlewares", lambda domain: catalog)
    commands = toolkit.run("middleware", "configure", *BASE,
                           "--middlewares-list", "postgresql", "apacheds", "httpd")
    assert [c[-3] for c in commands] == [
        toolkit.playbook("configure/BIP_LDP.yml"),
        toolkit.playbook("configure/PXY_RFM.yml"),
        toolkit.playbook("configure/RFM_SQL.yml"),
    ]


# --- middleware status / start / stop / restart ---------------------------

SERVICES = ["apacheds", "httpd", "sqlrfm", "ebx", "confluent"]


@pytest.mark.parametrize("subcommand, state", [
    ("status", "status"),
    ("start", "started"),
    ("stop", "stopped"),
    ("restart", "restarted"),
])
def test_middleware_systemd_un_playbook_par_service(toolkit, subcommand, state):
    expected = [
        toolkit.common() + [
            toolkit.playbook("exploit/systemd.yml"),
            "-e", f"{TP} app={service} env=DEV command={state}",
        ]
        for service in SERVICES
    ]
    assert toolkit.run("middleware", subcommand, *BASE) == expected


def test_middleware_restart_liste_reduite(toolkit):
    commands = toolkit.run("middleware", "restart", *BASE,
                           "--middlewares-list", "postgresql", "mck")
    assert [c[-1] for c in commands] == [
        f"{TP} app=sqlrfm env=DEV command=restarted",
        f"{TP} app=confluent env=DEV command=restarted",
    ]


def test_environnement_de_prod_utilise_la_ca_zpr(toolkit):
    commands = toolkit.run("initvm", "-p", "stackip", "--env", "ROP", "-i", "inv.yml")
    assert commands == [
        toolkit.common(ca=toolkit.zpr) + [
            toolkit.playbook("provision/init_vm.yml"),
            "-e", "tag_prefix=rfm_rop_stackip env=ROP",
            "-t", "idm, createfs, firewalld",
        ],
    ]
