#!/bin/env python

import argparse
import cisco
from cli import *
from cisco.acl import *
import time


def main(switch):
    if switch == '0':
        cli('conf t ; class-map type qos match-all mark_class_if_4 ; match access-group name acl_iter_1')

    elif switch == '1':
        cli('conf t ; class-map type qos match-all mark_class_if_4 ; no match access-group name acl_iter_1 ; match access-group name acl_iter_2')
        cli('conf t ; no ip access-list acl_iter_1')

    elif switch == '2':
        cli('conf t ; class-map type qos match-all mark_class_if_4 ; no match access-group name acl_iter_2 ; match access-group name acl_iter_1')
        cli('conf t ; no ip access-list acl_iter_2')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--switch', help='how to switch (-1, 0, 1, 2)')
    args = parser.parse_args()
    main(args.switch)
