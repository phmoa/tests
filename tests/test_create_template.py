"""Caractérisation : génération de .instances_compiled.yml et d'ansible.cfg."""
import yaml

from conftest import BASE, SECRET


def test_instances_compiled_fusionne_les_ancres_sans_alias(toolkit):
    toolkit.run("initvm", *BASE)
    text = toolkit.compiled().read_text()
    assert "&" not in text and "*" not in text
    assert yaml.safe_load(text) == {
        "httpd": {"cpu": 2, "ram": 4, "count": 1},
        "postgresql": {"cpu": 2, "ram": 4, "count": 2},
    }


def test_vault_est_interroge_avec_le_bon_chemin(toolkit):
    toolkit.run("initvm", *BASE)
    assert toolkit.vault.clients == [{
        "url": "https://vault.test:8200",
        "token": "token-de-test",
        "verify": toolkit.znp,
    }]
    assert toolkit.vault.reads == [{"path": "dev/stetuser", "mount_point": "kv/rip"}]


def test_ansible_cfg_contient_le_mot_de_passe_en_clair(toolkit):
    """PROBLÈME DE SÉCURITÉ ACTUEL : le secret Vault est écrit sur disque."""
    toolkit.run("initvm", *BASE)
    cfg = toolkit.ansible_cfg.read_text()
    assert f'ansible_become_pass = "{SECRET}"' in cfg
    assert 'ansible_user = "stetuser"' in cfg


def test_ansible_cfg_remplace_rootdir(toolkit):
    toolkit.run("initvm", *BASE)
    cfg = toolkit.ansible_cfg.read_text()
    assert f"roles_path = {toolkit.root}/ansible/roles" in cfg
    assert "{{" not in cfg


def test_create_template_est_lance_pour_toutes_les_commandes(toolkit):
    """Même un simple 'status' régénère ansible.cfg et interroge Vault."""
    toolkit.run("middleware", "status", *BASE, "--middlewares-list", "httpd")
    assert len(toolkit.vault.reads) == 1
    assert toolkit.ansible_cfg.exists()


def test_create_template_modifie_safedumper_pour_tout_le_processus(toolkit):
    """EFFET DE BORD ACTUEL : yaml.SafeDumper ne produit plus jamais d'alias."""
    toolkit.run("initvm", *BASE)
    shared = {"a": 1}
    assert "&" not in yaml.safe_dump({"x": shared, "y": shared})
