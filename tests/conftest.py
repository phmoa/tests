"""Phase 0 – tests de caractérisation du toolkit RIP.

Ces tests figent le comportement ACTUEL, bugs compris. Ils ne lancent jamais
Ansible et ne contactent jamais Vault :

- run_ansible_playbook est remplacé par un enregistreur ;
- hvac.Client est remplacé par un faux client ;
- root_dir pointe vers un bac à sable temporaire (votre vrai ansible.cfg
  n'est jamais touché).

Pour les lancer dans le vrai dépôt : copier le dossier tests/ à la racine,
puis `pip install -r tests/requirements.txt` et `pytest tests`.
"""
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "engine"))

import hvac  # noqa: E402
from helpers import global_args_parser, rfm_manager, utils  # noqa: E402
from ip import wrapper  # noqa: E402

# Arguments obligatoires communs à toutes les commandes
BASE = ["-p", "stackip", "--env", "dev", "-i", "inv.yml"]

SECRET = "s3cret-de-test"

MIDDLEWARES_YML = """\
_defaults:
  small: &small
    cpu: 2
    ram: 4
"""

INSTANCES_YML = """\
INSTANCES:
  httpd:
    <<: *small
    count: 1
  postgresql:
    <<: *small
    count: 2
"""


def make_config_dir(path: Path, envs=("DEV", "ROP")) -> Path:
    """Crée un répertoire de configuration minimal (sizing + infra + CA)."""
    ca = path / "certificates" / "ca"
    ca.mkdir(parents=True)
    (ca / "znp_zac_stet.crt").write_text("CA ZNP\n")
    (ca / "zpr_zac_stet.crt").write_text("CA ZPR\n")
    for env in envs:
        sizing = path / "sizing" / env
        sizing.mkdir(parents=True)
        (sizing / "middlewares.yml").write_text(MIDDLEWARES_YML)
        (sizing / "instances-ip.yml").write_text(INSTANCES_YML)
        infra = path / "infra" / env
        infra.mkdir(parents=True)
        (infra / "main.yml").write_text("vault:\n  url: https://vault.test:8200\n")
    return path


@dataclass
class FakeVault:
    """Enregistre les appels faits à Vault."""
    clients: list = field(default_factory=list)
    reads: list = field(default_factory=list)

    def factory(self):
        vault = self

        class _KV2:
            def read_secret_version(self, path, mount_point):
                vault.reads.append({"path": path, "mount_point": mount_point})
                return {"data": {"data": {"password": SECRET}}}

        class _Client:
            def __init__(self, url, token, verify):
                vault.clients.append({"url": url, "token": token, "verify": verify})
                self.secrets = type("S", (), {"kv": type("K", (), {"v2": _KV2()})()})()

        return _Client


class Recorder:
    """Remplace run_ansible_playbook : note chaque commande au lieu de la lancer."""

    def __init__(self):
        self.commands = []
        self.fail_with = None

    def __call__(self, cmd):
        # Copie : validate() modifie la même liste après l'appel.
        self.commands.append(list(cmd))
        if self.fail_with is not None:
            raise subprocess.CalledProcessError(self.fail_with, cmd)


@dataclass
class Toolkit:
    root: Path
    recorder: Recorder
    vault: FakeVault
    monkeypatch: pytest.MonkeyPatch

    # --- lancement -------------------------------------------------------
    def run(self, *argv):
        self.monkeypatch.setattr(sys, "argv", ["wrapper.py", *argv])
        wrapper.main()
        return self.recorder.commands

    @property
    def commands(self):
        return self.recorder.commands

    # --- chemins du bac à sable -----------------------------------------
    @property
    def config(self) -> Path:
        return self.root / ".config"

    @property
    def znp(self) -> str:
        return str(self.config / "certificates" / "ca" / "znp_zac_stet.crt")

    @property
    def zpr(self) -> str:
        return str(self.config / "certificates" / "ca" / "zpr_zac_stet.crt")

    @property
    def ansible_cfg(self) -> Path:
        return self.root / "ansible" / "ansible.cfg"

    def compiled(self, env="DEV") -> Path:
        return self.root / ".instances_compiled_files" / "ip" / env / ".instances_compiled.yml"

    def playbook(self, rel: str) -> str:
        return f"{self.root}/ansible/playbooks/{rel}"

    # --- début de commande commun à tous les appels ----------------------
    def common(self, ca=None, executable=None, configdir=None, inventory="inv.yml"):
        ca = ca or self.znp
        executable = executable or f"{self.root}/.env/bin/ansible-playbook"
        configdir = os.path.realpath(configdir or f"{self.root}/.config/")
        return [
            executable, "-i", inventory,
            "-e", f"ca_cert={ca}",
            "-e", f"root_dir={self.root} config_dir={configdir} business_domain=ip rfm_vault=rip",
        ]


@pytest.fixture
def toolkit(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    (root / "ansible").mkdir(parents=True)
    shutil.copy(REPO / "ansible" / "ansible.cfg.tpl", root / "ansible" / "ansible.cfg.tpl")
    make_config_dir(root / ".config")
    for env in ("DEV", "ROP"):
        compiled = root / ".instances_compiled_files" / "ip" / env
        compiled.mkdir(parents=True)
        (compiled / ".instances_compiled.yml").write_text("")

    # root_dir est importé par valeur dans chaque module : on le remplace partout.
    for module in (rfm_manager, utils, global_args_parser):
        monkeypatch.setattr(module, "root_dir", str(root))

    # Les chemins des CA sont calculés à l'import depuis le vrai config_dir.
    ca_dir = root / ".config" / "certificates" / "ca"
    fake_ca = Enum("CAPaths", {
        "ZNP_ZAC_STET_CA": str(ca_dir / "znp_zac_stet.crt"),
        "ZPR_ZAC_STET_CA": str(ca_dir / "zpr_zac_stet.crt"),
    })
    monkeypatch.setattr(utils, "CAPaths", fake_ca)

    monkeypatch.setenv("VAULT_TOKEN", "token-de-test")
    monkeypatch.delenv("DOCKER_MODE", raising=False)
    monkeypatch.delenv("docker_mode", raising=False)

    vault = FakeVault()
    monkeypatch.setattr(hvac, "Client", vault.factory())

    recorder = Recorder()
    monkeypatch.setattr(rfm_manager, "run_ansible_playbook", recorder)

    return Toolkit(root=root, recorder=recorder, vault=vault, monkeypatch=monkeypatch)
