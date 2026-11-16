# =============================================================================
# conftest.py — VERSION COMPLÈTE (étape 3)
# =============================================================================
# Rappel : pytest charge ce fichier AUTOMATIQUEMENT avant tous les tests du
# dossier tests/. On n'a jamais besoin de l'importer soi-même.
#
# À l'étape 1, il ne faisait qu'une chose : ajouter engine/ à sys.path.
# Il contient maintenant tout ce qu'il faut pour lancer le VRAI toolkit dans
# un test, sans aucun effet sur le monde réel :
#
#   - Ansible n'est jamais lancé : run_ansible_playbook est remplacé par un
#     "enregistreur" qui note les commandes au lieu de les exécuter ;
#   - Vault n'est jamais contacté : hvac.Client est remplacé par un faux client ;
#   - aucun vrai fichier n'est modifié : root_dir pointe vers un dossier
#     temporaire (le "bac à sable"), donc votre vrai ansible.cfg n'est jamais
#     écrasé.
#
# Le code du toolkit (engine/) n'est PAS modifié : on remplace ces éléments
# uniquement le temps d'un test, avec "monkeypatch" (expliqué plus bas).
#
# Plan du fichier :
#   1. imports et sys.path                  (sous-tâche 1.1, déjà vue)
#   2. constantes                           (sous-tâche 3.1)
#   3. make_config_dir()                    (sous-tâche 3.2)
#   4. FakeVault                            (sous-tâche 3.4)
#   5. Recorder                             (sous-tâche 3.3)
#   6. Toolkit                              (sous-tâche 3.5)
#   7. la fixture toolkit                   (sous-tâche 3.6)
# =============================================================================


# =============================================================================
# 1. IMPORTS ET sys.path
# =============================================================================

# os : pour os.path.realpath, que le toolkit utilise sur --config-dir.
import os

# shutil : pour copier un fichier (shutil.copy).
import shutil

# subprocess : on en a besoin pour fabriquer la même erreur que lancerait un
# vrai échec d'Ansible (subprocess.CalledProcessError).
import subprocess

# sys : pour sys.path (étape 1) et sys.argv (les arguments de la ligne de
# commande, qu'on remplacera pour simuler "bin/toolkit initvm -p ...").
import sys

# dataclass : écrit automatiquement le __init__ d'une classe à partir de ses
# attributs. field : permet de donner une valeur par défaut "liste vide".
from dataclasses import dataclass, field

# Enum : pour fabriquer un faux CAPaths (voir la fixture).
from enum import Enum

# Path : manipulation des chemins (déjà vu à l'étape 1).
from pathlib import Path

# pytest lui-même : pour @pytest.fixture et le type pytest.MonkeyPatch.
import pytest

# --- La partie de l'étape 1, inchangée ---------------------------------------
# REPO = la racine du dépôt (tests/ est un niveau en dessous).
REPO = Path(__file__).resolve().parents[1]
# engine/ en tête de sys.path, pour que "from helpers import ..." fonctionne.
sys.path.insert(0, str(REPO / "engine"))

# --- Les modules du toolkit qu'on va manipuler -------------------------------
# Ces imports doivent venir APRÈS le sys.path.insert : avant, Python ne
# saurait pas où trouver "helpers" et "ip".
# "# noqa: E402" dit aux outils de style (ruff, flake8) de ne pas signaler
# ces imports placés après du code : c'est volontaire.
import hvac  # noqa: E402  (la bibliothèque Vault, dont on remplacera Client)
from helpers import global_args_parser, rfm_manager, utils  # noqa: E402
from ip import wrapper  # noqa: E402  (le point d'entrée : wrapper.main())


# =============================================================================
# 2. CONSTANTES (sous-tâche 3.1)
# =============================================================================
# Des valeurs réutilisées par plusieurs fichiers de test. Par convention, une
# constante s'écrit en MAJUSCULES.

# Les arguments obligatoires de toutes les commandes du toolkit :
#   -p stackip      : le préfixe de la stack
#   --env dev       : l'environnement
#   -i inv.yml      : l'inventaire (le fichier n'a pas besoin d'exister :
#                     Ansible n'est jamais lancé)
# Dans un test, on écrira par exemple :  toolkit.run("initvm", *BASE)
# L'étoile "*" déplie la liste : c'est comme écrire
#     toolkit.run("initvm", "-p", "stackip", "--env", "dev", "-i", "inv.yml")
BASE = ["-p", "stackip", "--env", "dev", "-i", "inv.yml"]

# Le faux mot de passe que renverra notre faux Vault. Un test vérifiera qu'il
# se retrouve en clair dans ansible.cfg (le problème de sécurité actuel).
SECRET = "s3cret-de-test"

# Le contenu des deux faux fichiers de "sizing" lus par create_template().
# Le vrai code les CONCATÈNE en texte avant de les lire en YAML : c'est ce qui
# permet au second fichier d'utiliser une ancre (&small) définie dans le
# premier (*small). On reproduit volontairement cette astuce.
#
# Le "\" juste après les triples guillemets évite une ligne vide au début.
MIDDLEWARES_YML = """\
_defaults:
  small: &small
    cpu: 2
    ram: 4
"""

# "<<: *small" signifie : "recopie ici le contenu de l'ancre small".
# create_template() ne garde que la clé INSTANCES.
INSTANCES_YML = """\
INSTANCES:
  httpd:
    <<: *small
    count: 1
  postgresql:
    <<: *small
    count: 2
"""


# =============================================================================
# 3. make_config_dir() (sous-tâche 3.2)
# =============================================================================
# Crée, dans le dossier "path", la plus petite arborescence de configuration
# dont le toolkit a besoin pour démarrer :
#
#   path/
#   ├── certificates/ca/znp_zac_stet.crt      (CA hors production)
#   ├── certificates/ca/zpr_zac_stet.crt      (CA de production)
#   ├── sizing/DEV/middlewares.yml
#   ├── sizing/DEV/instances-ip.yml
#   ├── infra/DEV/main.yml                    (contient l'URL de Vault)
#   └── ... la même chose pour ROP
#
# C'est une fonction "normale" (pas une fixture) : un test peut l'appeler
# lui-même pour créer un second répertoire de configuration, par exemple pour
# tester l'option --config-dir.
#
# "path: Path" et "-> Path" sont des annotations de type : elles documentent
# ce que la fonction attend et renvoie. Python ne les vérifie pas.
def make_config_dir(path: Path, envs=("DEV", "ROP")) -> Path:
    """Crée un répertoire de configuration minimal (sizing + infra + CA)."""
    # L'opérateur "/" entre un Path et une chaîne construit un sous-chemin.
    ca = path / "certificates" / "ca"
    # parents=True : crée aussi les dossiers intermédiaires (comme mkdir -p).
    ca.mkdir(parents=True)
    # write_text() crée le fichier et y écrit le texte. Le contenu importe peu :
    # le toolkit vérifie seulement que le certificat EXISTE.
    (ca / "znp_zac_stet.crt").write_text("CA ZNP\n")
    (ca / "zpr_zac_stet.crt").write_text("CA ZPR\n")

    # Un jeu de fichiers par environnement. Le toolkit met l'environnement en
    # majuscules (args.env.upper()), d'où "DEV" et "ROP".
    for env in envs:
        sizing = path / "sizing" / env
        sizing.mkdir(parents=True)
        (sizing / "middlewares.yml").write_text(MIDDLEWARES_YML)
        (sizing / "instances-ip.yml").write_text(INSTANCES_YML)

        infra = path / "infra" / env
        infra.mkdir(parents=True)
        # create_template() lit infra["vault"]["url"] pour créer le client Vault.
        (infra / "main.yml").write_text("vault:\n  url: https://vault.test:8200\n")

    # On renvoie le chemin pour pouvoir écrire :  other = make_config_dir(...)
    return path


# =============================================================================
# 4. FakeVault (sous-tâche 3.4)
# =============================================================================
# Le vrai code fait, dans create_template() :
#
#     client = hvac.Client(url=..., token=..., verify=...)
#     client.secrets.kv.v2.read_secret_version(path=..., mount_point=...)
#
# On veut remplacer hvac.Client par une fausse classe qui :
#   - accepte les mêmes arguments ;
#   - offre le même chemin d'accès  client.secrets.kv.v2.read_secret_version ;
#   - NOTE chaque appel, pour que les tests puissent vérifier ce qui a été
#     demandé ;
#   - renvoie le faux mot de passe SECRET, dans le même format que Vault.
#
# @dataclass écrit le __init__ automatiquement. Les deux attributs sont des
# listes qui démarrent vides. "field(default_factory=list)" est la façon
# correcte de donner une liste vide par défaut : chaque FakeVault a SA propre
# liste (avec "= []", toutes les instances partageraient la même).
@dataclass
class FakeVault:
    """Enregistre les appels faits à Vault."""
    clients: list = field(default_factory=list)   # un élément par hvac.Client(...) créé
    reads: list = field(default_factory=list)     # un élément par secret lu

    def factory(self):
        """Fabrique et renvoie la fausse classe à mettre à la place de hvac.Client."""
        # Les classes définies plus bas ont besoin d'écrire dans CE FakeVault.
        # À l'intérieur de leurs méthodes, "self" désignera l'objet de la
        # fausse classe, pas le FakeVault : on garde donc une référence au
        # FakeVault sous un autre nom.
        vault = self

        # Imite l'objet "client.secrets.kv.v2".
        class _KV2:
            def read_secret_version(self, path, mount_point):
                # On note ce qui a été demandé...
                vault.reads.append({"path": path, "mount_point": mount_point})
                # ...et on renvoie la même structure que la vraie réponse de
                # Vault, que le toolkit lit avec ["data"]["data"]["password"].
                return {"data": {"data": {"password": SECRET}}}

        # Imite hvac.Client.
        class _Client:
            def __init__(self, url, token, verify):
                # On note avec quels paramètres le client a été créé.
                vault.clients.append({"url": url, "token": token, "verify": verify})
                # Le toolkit accède à  client.secrets.kv.v2  : il faut donc
                # que self.secrets ait un attribut kv, qui a un attribut v2.
                # type("S", (), {...}) crée une classe à la volée, avec les
                # attributs donnés dans le dictionnaire ; le "()" final crée
                # une instance. Lu de l'intérieur vers l'extérieur :
                #   K()  a un attribut v2 = _KV2()
                #   S()  a un attribut kv = K()
                # donc self.secrets.kv.v2 est un _KV2.
                self.secrets = type("S", (), {"kv": type("K", (), {"v2": _KV2()})()})()

        # On renvoie la CLASSE (pas une instance) : le toolkit fera lui-même
        # _Client(url=..., token=..., verify=...).
        return _Client


# =============================================================================
# 5. Recorder (sous-tâche 3.3)
# =============================================================================
# Remplace run_ansible_playbook(cmd). Au lieu de lancer Ansible, il note la
# commande. Un test peut ensuite comparer la liste des commandes notées à ce
# qu'il attend.
#
# La méthode spéciale __call__ permet d'utiliser un objet COMME une fonction :
#     recorder = Recorder()
#     recorder(["ansible-playbook", ...])    # appelle recorder.__call__(...)
# Le toolkit appelle donc notre enregistreur exactement comme il appelait
# run_ansible_playbook, sans voir la différence.
class Recorder:
    """Remplace run_ansible_playbook : note chaque commande au lieu de la lancer."""

    def __init__(self):
        # La liste des commandes reçues, dans l'ordre.
        self.commands = []
        # Si un test met ici un code retour (par ex. 4), l'enregistreur
        # simulera un échec d'Ansible avec ce code.
        self.fail_with = None

    def __call__(self, cmd):
        # list(cmd) fait une COPIE de la liste. C'est indispensable :
        # validate() continue de modifier la même liste (cmd.append(...))
        # après l'avoir passée à run_ansible_playbook. Sans copie, toutes les
        # commandes notées changeraient en même temps.
        self.commands.append(list(cmd))
        # Simulation d'un échec : c'est l'erreur que lève le vrai
        # subprocess.run(..., check=True) quand Ansible sort en erreur.
        if self.fail_with is not None:
            raise subprocess.CalledProcessError(self.fail_with, cmd)


# =============================================================================
# 6. Toolkit (sous-tâche 3.5)
# =============================================================================
# L'objet que les tests manipulent. Il regroupe :
#   - run(...)              : lancer le toolkit avec des arguments ;
#   - commands              : les commandes Ansible qu'il a produites ;
#   - des chemins pratiques dans le bac à sable (config, znp, ansible_cfg...) ;
#   - common(...)           : le début de commande commun à tous les appels.
#
# Un test l'utilise ainsi :
#     def test_initvm(toolkit):
#         toolkit.run("initvm", *BASE)
#         assert toolkit.commands == [...]
#
# @dataclass écrit le __init__ à partir des quatre attributs ci-dessous.
@dataclass
class Toolkit:
    root: Path                       # la racine du bac à sable (le faux dépôt)
    recorder: Recorder               # l'enregistreur de commandes
    vault: FakeVault                 # le faux Vault
    monkeypatch: pytest.MonkeyPatch  # gardé pour que les tests puissent
                                     # modifier l'environnement eux-mêmes

    # --- lancement -----------------------------------------------------------
    def run(self, *argv):
        """Lance le vrai wrapper.main() comme si on tapait : bin/toolkit <argv>."""
        # *argv reçoit tous les arguments sous forme de tuple :
        #   toolkit.run("initvm", "-p", "x")  ->  argv = ("initvm", "-p", "x")
        #
        # argparse lit les arguments dans sys.argv. sys.argv[0] est le nom du
        # programme, les arguments viennent ensuite. On remplace sys.argv le
        # temps du test : monkeypatch le remettra en place à la fin.
        self.monkeypatch.setattr(sys, "argv", ["wrapper.py", *argv])
        # Le VRAI point d'entrée du toolkit, sans aucune modification.
        wrapper.main()
        # On renvoie les commandes notées, pour pouvoir écrire :
        #     assert toolkit.run("initvm", *BASE) == [...]
        return self.recorder.commands

    # @property transforme une méthode en attribut calculé : on écrit
    # toolkit.commands (sans parenthèses) et la méthode est appelée.
    @property
    def commands(self):
        return self.recorder.commands

    # --- chemins du bac à sable ----------------------------------------------
    # Raccourcis pour ne pas recalculer ces chemins dans chaque test.

    @property
    def config(self) -> Path:
        # Le répertoire de configuration par défaut du toolkit : root_dir/.config
        return self.root / ".config"

    @property
    def znp(self) -> str:
        # Le certificat CA hors production. En str, car le toolkit le met
        # dans une chaîne ("ca_cert=...").
        return str(self.config / "certificates" / "ca" / "znp_zac_stet.crt")

    @property
    def zpr(self) -> str:
        # Le certificat CA de production.
        return str(self.config / "certificates" / "ca" / "zpr_zac_stet.crt")

    @property
    def ansible_cfg(self) -> Path:
        # Le fichier généré par create_template().
        return self.root / "ansible" / "ansible.cfg"

    def compiled(self, env="DEV") -> Path:
        # Le fichier .instances_compiled.yml d'un environnement.
        return self.root / ".instances_compiled_files" / "ip" / env / ".instances_compiled.yml"

    def playbook(self, rel: str) -> str:
        # Le chemin complet d'un playbook, tel que le toolkit l'écrit dans
        # la commande. Ex. : toolkit.playbook("provision/init_vm.yml")
        return f"{self.root}/ansible/playbooks/{rel}"

    # --- début de commande commun à tous les appels --------------------------
    def common(self, ca=None, executable=None, configdir=None, inventory="inv.yml"):
        """Reproduit get_ansible_cmd_common_params() pour les cas sans option.

        Toutes les commandes du toolkit commencent par les mêmes éléments :
        l'exécutable, l'inventaire, le certificat CA et les variables
        communes. Les tests écrivent  toolkit.common() + [la suite]  au lieu
        de recopier ce début dans chaque test.

        Les paramètres permettent de changer ce qui varie d'un test à l'autre :
        la CA de production, l'exécutable en mode Docker, un autre
        --config-dir, un autre inventaire.
        """
        # "a or b" vaut b quand a est None : c'est la valeur par défaut.
        ca = ca or self.znp
        executable = executable or f"{self.root}/.env/bin/ansible-playbook"
        # Le toolkit passe --config-dir dans os.path.realpath() : on fait
        # pareil pour obtenir exactement la même chaîne.
        configdir = os.path.realpath(configdir or f"{self.root}/.config/")
        return [
            executable, "-i", inventory,
            "-e", f"ca_cert={ca}",
            "-e", f"root_dir={self.root} config_dir={configdir} business_domain=ip rfm_vault=rip",
        ]


# =============================================================================
# 7. LA FIXTURE toolkit (sous-tâche 3.6)
# =============================================================================
# Une FIXTURE est une fonction que pytest appelle AVANT un test pour lui
# préparer quelque chose. Un test la demande simplement en la nommant dans
# ses paramètres :
#
#     def test_initvm(toolkit):     # pytest voit "toolkit", appelle la
#         ...                       # fixture ci-dessous et passe son résultat
#
# Chaque test reçoit une fixture NEUVE : les tests ne se gênent jamais entre
# eux.
#
# Cette fixture utilise elle-même deux fixtures fournies par pytest :
#   - tmp_path    : un dossier temporaire vide, différent pour chaque test,
#                   supprimé automatiquement plus tard ;
#   - monkeypatch : l'outil qui remplace un élément du code PENDANT le test,
#                   puis remet automatiquement l'original à la fin. C'est
#                   lui qui permet de ne jamais modifier le code d'engine/.
@pytest.fixture
def toolkit(tmp_path, monkeypatch):
    # --- 7a. Le bac à sable : un faux dépôt dans le dossier temporaire --------
    root = tmp_path / "repo"
    (root / "ansible").mkdir(parents=True)

    # create_template() lit le template ansible.cfg.tpl : on copie le VRAI
    # template du dépôt dans le bac à sable. Le ansible.cfg qu'il générera
    # sera donc écrit dans le bac à sable, pas dans votre dépôt.
    shutil.copy(REPO / "ansible" / "ansible.cfg.tpl", root / "ansible" / "ansible.cfg.tpl")

    # La configuration par défaut : root_dir/.config
    make_config_dir(root / ".config")

    # wrapper.py vérifie que .instances_compiled.yml existe AVANT d'appeler
    # create_template() (qui sait pourtant le générer). On crée donc des
    # fichiers vides, sinon le toolkit s'arrêterait tout de suite.
    for env in ("DEV", "ROP"):
        compiled = root / ".instances_compiled_files" / "ip" / env
        compiled.mkdir(parents=True)
        (compiled / ".instances_compiled.yml").write_text("")

    # --- 7b. Rediriger root_dir vers le bac à sable --------------------------
    # root_dir est calculé une fois, dans global_vars.py. Mais chaque module
    # qui fait "from helpers.global_vars import root_dir" en garde SA PROPRE
    # copie. Modifier global_vars.root_dir ne suffirait donc pas : il faut
    # remplacer la copie de chaque module qui l'utilise.
    #
    # monkeypatch.setattr(module, "nom", valeur) remplace module.nom par
    # valeur pendant le test, et remet l'ancienne valeur à la fin.
    for module in (rfm_manager, utils, global_args_parser):
        monkeypatch.setattr(module, "root_dir", str(root))

    # --- 7c. Rediriger les chemins des certificats CA ------------------------
    # CAPaths est un Enum dont les valeurs ont été calculées À L'IMPORT, à
    # partir du vrai config_dir. On ne peut pas modifier les valeurs d'un
    # Enum existant : on en fabrique un nouveau, avec les mêmes noms, qui
    # pointe vers les certificats du bac à sable, et on le met à la place
    # de l'original dans utils (qui l'utilise dans get_stet_ca_name()).
    ca_dir = root / ".config" / "certificates" / "ca"
    fake_ca = Enum("CAPaths", {
        "ZNP_ZAC_STET_CA": str(ca_dir / "znp_zac_stet.crt"),
        "ZPR_ZAC_STET_CA": str(ca_dir / "zpr_zac_stet.crt"),
    })
    monkeypatch.setattr(utils, "CAPaths", fake_ca)

    # --- 7d. Les variables d'environnement -----------------------------------
    # create_template() exige VAULT_TOKEN : on en donne un faux.
    monkeypatch.setenv("VAULT_TOKEN", "token-de-test")
    # Si DOCKER_MODE est défini sur votre poste, le toolkit changerait
    # d'exécutable. On le retire pour que les tests donnent le même résultat
    # partout. raising=False : pas d'erreur si la variable n'existait pas.
    monkeypatch.delenv("DOCKER_MODE", raising=False)
    monkeypatch.delenv("docker_mode", raising=False)

    # --- 7e. Remplacer Vault --------------------------------------------------
    # rfm_manager fait "import hvac" puis "hvac.Client(...)" : il va chercher
    # Client dans le module hvac au moment de l'appel. Remplacer hvac.Client
    # suffit donc.
    vault = FakeVault()
    monkeypatch.setattr(hvac, "Client", vault.factory())

    # --- 7f. Remplacer Ansible ------------------------------------------------
    # rfm_manager fait "from helpers.utils import run_ansible_playbook" : il a
    # sa PROPRE référence à la fonction. C'est donc dans rfm_manager qu'il
    # faut la remplacer (la remplacer dans utils ne changerait rien).
    recorder = Recorder()
    monkeypatch.setattr(rfm_manager, "run_ansible_playbook", recorder)

    # --- 7g. Tout donner au test ----------------------------------------------
    # "return" : ce que reçoit le paramètre "toolkit" du test.
    return Toolkit(root=root, recorder=recorder, vault=vault, monkeypatch=monkeypatch)
