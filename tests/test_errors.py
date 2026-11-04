"""Caractérisation : comportement en cas d'erreur."""
import subprocess

import pytest

from conftest import BASE


def test_sans_commande_affiche_l_aide_et_sort_en_1(toolkit, capsys):
    with pytest.raises(SystemExit) as exc:
        toolkit.run()
    assert exc.value.code == 1
    assert "usage: toolkit" in capsys.readouterr().out


def test_middleware_sans_sous_commande_plante(toolkit):
    """BUG ACTUEL : trace Python au lieu de l'aide."""
    with pytest.raises(AttributeError, match="env"):
        toolkit.run("middleware")


def test_middleware_inconnu_refuse_par_argparse(toolkit):
    with pytest.raises(SystemExit) as exc:
        toolkit.run("middleware", "install", *BASE, "--middlewares-list", "nginx")
    assert exc.value.code == 2
    assert toolkit.commands == []


def test_syntaxe_des_exemples_de_l_aide_refusee(toolkit):
    """BUG ACTUEL : l'aide montre {httpd,ebx,postgresql}, qu'argparse refuse."""
    with pytest.raises(SystemExit) as exc:
        toolkit.run("middleware", "uninstall", *BASE,
                    "--middlewares-list", "{httpd,ebx,postgresql}")
    assert exc.value.code == 2


@pytest.mark.parametrize("option", ["--dry-run", "--reinstall"])
def test_options_prevues_dans_le_code_mais_inexistantes(toolkit, option):
    with pytest.raises(SystemExit) as exc:
        toolkit.run("middleware", "install", *BASE, option)
    assert exc.value.code == 2


def test_prefix_obligatoire(toolkit):
    with pytest.raises(SystemExit) as exc:
        toolkit.run("initvm", "--env", "dev", "-i", "inv.yml")
    assert exc.value.code == 2


def test_env_insensible_a_la_casse(toolkit):
    toolkit.run("initvm", "-p", "stackip", "--env", "DEV", "-i", "inv.yml")
    assert len(toolkit.commands) == 1


def test_certificat_ca_absent(toolkit, capsys):
    (toolkit.config / "certificates" / "ca" / "znp_zac_stet.crt").unlink()
    with pytest.raises(SystemExit) as exc:
        toolkit.run("initvm", *BASE)
    assert exc.value.code == 1
    assert "Le certificat CA" in capsys.readouterr().out
    assert toolkit.commands == []


def test_fichier_instances_compiled_absent(toolkit, capsys):
    """Le contrôle a lieu AVANT create_template(), qui sait pourtant le générer."""
    toolkit.compiled().unlink()
    with pytest.raises(SystemExit) as exc:
        toolkit.run("initvm", *BASE)
    assert exc.value.code == 1
    assert "generer_instance_compile.py" in capsys.readouterr().out


def test_vault_token_absent_vide_ansible_cfg(toolkit):
    """BUG ACTUEL : ansible.cfg est vidé avant la vérification du token."""
    toolkit.ansible_cfg.write_text("[defaults]\nancienne configuration\n")
    toolkit.monkeypatch.delenv("VAULT_TOKEN")
    with pytest.raises(RuntimeError, match="VAULT_TOKEN"):
        toolkit.run("initvm", *BASE)
    assert toolkit.ansible_cfg.read_text() == ""
    assert toolkit.commands == []


def test_echec_ansible_remonte_une_trace_python(toolkit):
    """BUG ACTUEL : CalledProcessError non attrapée, code retour d'Ansible perdu."""
    toolkit.recorder.fail_with = 4
    with pytest.raises(subprocess.CalledProcessError) as exc:
        toolkit.run("initvm", *BASE)
    assert exc.value.returncode == 4


def test_echec_ansible_arrete_la_boucle(toolkit):
    toolkit.recorder.fail_with = 2
    with pytest.raises(subprocess.CalledProcessError):
        toolkit.run("middleware", "restart", *BASE)
    assert len(toolkit.commands) == 1
