# Phase 0 – Tests de caractérisation

Ces 64 tests figent le comportement **actuel** du toolkit RIP, bugs compris.
Ils ne lancent jamais Ansible, ne contactent jamais Vault et ne touchent pas
à votre `ansible/ansible.cfg` : tout se passe dans un répertoire temporaire.

## Lancer les tests sur le vrai dépôt

```bash
cp -r tests/ /chemin/vers/rfm-toolkit/
cd /chemin/vers/rfm-toolkit
source .env/bin/activate            # ou un venv dédié
pip install -r tests/requirements.txt
pytest tests -v
```

Le code de ce dossier a été recopié depuis des photos. Si un test échoue sur
le vrai dépôt, c'est soit une erreur de transcription, soit une différence
entre les photos et le code : il faut alors corriger le test, pas le code.

Seuls les textes d'aide (`epilog`) de `ip/args_parser.py` ont été abrégés
lors de la transcription ; ils n'influencent aucun test.

## Ce que contient chaque fichier

| Fichier | Couvre |
| --- | --- |
| `conftest.py` | Bac à sable, enregistreur de commandes, faux Vault |
| `test_commands.py` | `initvm`, `deploy`, `validate`, `middleware *` |
| `test_filters_options.py` | `--middlewares-list`, `--zones-list`, `--zone`, `--middleware`, `-v`, `-e`, `--docker`, `-c` |
| `test_create_template.py` | `.instances_compiled.yml`, `ansible.cfg`, appels Vault |
| `test_errors.py` | Arguments invalides, fichiers absents, `VAULT_TOKEN` absent, échec d'Ansible |
| `test_utils.py` | `get_default_middlewares`, `get_stet_ca_name`, listes de services |

## Les tests qui documentent un bug

Leur docstring commence par `BUG ACTUEL`, `PROBLÈME DE SÉCURITÉ ACTUEL`,
`EFFET DE BORD ACTUEL` ou `PIÈGE ACTUEL`. Quand un bug est corrigé en phase 1,
le test correspondant est modifié **dans le même commit** pour décrire le
nouveau comportement.

```bash
grep -n "ACTUEL" tests/*.py
```
