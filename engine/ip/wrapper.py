#!/usr/bin/env python3
""" Main script to create RIP stack """
# -*- coding: utf-8 -*-
from ip.args_parser import get_rip_parser
from ip.rip import RIPToolKit

from helpers.global_vars import RFMBusinessDomains
from helpers.global_args_parser import get_tookit_args
from helpers.utils import check_instance_compile_file


def main():
    """ RIP Wrapper Main """
    args = get_tookit_args(get_rip_parser)
    rip = RIPToolKit(args, RFMBusinessDomains.IP.value)
    check_instance_compile_file(RFMBusinessDomains.IP.value, rip.env)

    # stack complete
    # il n'y a pas de notions de version ou d'image (comme sur sabr)
    # crée les fichiers a partir des templates
    rip.create_template()
    rip.compile()


#  il faut créer l'environnement d'exécution a l'image de env-setup.sh
if __name__ == "__main__":
    main()
