#!/bin/env python

import argparse
import cisco
from cli import *
from cisco.acl import *
import time


def main(cmd):
    new_cmd = ""
    for c in cmd:
        if c != 'q':
            new_cmd += c
        else:
            new_cmd += ' '

    cli(new_cmd)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cmd', help='cmd')
    args = parser.parse_args()
    main(args.cmd)
