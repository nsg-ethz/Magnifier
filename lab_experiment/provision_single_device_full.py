#!/bin/env python

import argparse
import cisco
from cli import *
from cisco.acl import *
import time


def main(prefixes, device, iteration):
    if device == '1':
        dst = ' 0.0.0.0/2'
        counter = 1001
        if iteration == '1':
            cmd_start = 'conf t ; ip access-list acl_iter_1'
        elif iteration == '2':
            cmd_start = 'conf t ; ip access-list acl_iter_2'
    elif device == '2':
        dst = ' 64.0.0.0/2'
        counter = 2001
        if iteration == '1':
            cmd_start = 'conf t ; ip access-list acl_iter_1'
        elif iteration == '2':
            cmd_start = 'conf t ; ip access-list acl_iter_2'
    elif device == '3':
        dst = ' 128.0.0.0/2'
        counter = 3001
        if iteration == '1':
            cmd_start = 'conf t ; ip access-list acl_iter_1'
        elif iteration == '2':
            cmd_start = 'conf t ; ip access-list acl_iter_2'
    elif device == '4':
        dst = ' 192.0.0.0/2'
        counter = 4001
        if iteration == '1':
            cmd_start = 'conf t ; ip access-list acl_iter_1'
        elif iteration == '2':
            cmd_start = 'conf t ; ip access-list acl_iter_2'

    cmd_string = cmd_start
    if prefixes != '-':
        for prefix in prefixes.strip().split(','):
            cmd_string += ' ; ' + str(counter) + ' permit ip ' + prefix + dst
            counter += 1

    cli(cmd_string)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--p', help='prefixes to add')
    parser.add_argument('--dev', help='on which device (1, 2, 3, 4)')
    parser.add_argument('--iter', help='iteration 1 or 2')
    args = parser.parse_args()
    main(args.p, args.dev, args.iter)
