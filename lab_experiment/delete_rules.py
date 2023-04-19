import argparse
import time
import pytricia
from util.ip_conversion import ipv4_to_int
import subprocess
from collections import defaultdict


ROUTER_TO_DST = {1: 'q0.0.0.0/2', 2: 'q64.0.0.0/2', 3: 'q128.0.0.0/2', 4: 'q192.0.0.0/2'}


def get_router(ip):
    if 0 <= ip < 1073741824:
        return 1
    if 1073741824 <= ip < 2147483648:
        return 2
    if 2147483648 <= ip < 3221225472:
        return 3
    if 3221225472 <= ip:
        return 4


def main(p1, p2, p3, p4, iteration):
    prefixes = [p1, p2 ,p3 ,p4]
    counter = [1001, 2001, 3001, 4001]
    trees = [pytricia.PyTricia(), pytricia.PyTricia(), pytricia.PyTricia(), pytricia.PyTricia()]
    for i in range(4):
        if prefixes[i] != '-':
            for prefix in prefixes[i].strip().split(','):
                trees[i][prefix] = counter[i]
                counter[i] += 1

    with open('mirrored/dummy.csv', 'r') as data_in:
        for i, line in enumerate(data_in):
            continue

    last_pkt = i

    # max 1 times
    for iii in range(1):
        time.sleep(2)

        cmd = 'confqtq;qipqaccess-listqacl_iter_{}'.format(iteration)

        mirrored_dict = defaultdict(int)

        with open('mirrored/dummy.csv', 'r') as data_in:
            for i, line in enumerate(data_in):
                if i < last_pkt:
                    continue

                cells = line.strip().split(',')
                if len(cells) != 11:
                    continue
                if cells[8] == "" or cells[10] == "":
                    continue

                try:
                    dst_ip = ipv4_to_int(cells[10])
                except OSError:
                    # print('invalid IPs in', cells[8], cells[10])
                    continue

                router = get_router(dst_ip)

                if cells[8] in trees[router-1]:
                    key = trees[router-1].get_key(cells[8])
                    tree_counter = trees[router-1][cells[8]]

                    dict_key = str(tree_counter)+'-'+key+'-'+ROUTER_TO_DST[router]
                    mirrored_dict[dict_key] += 1

        temp = list()
        for key, value in mirrored_dict.items():
            temp.append((key, value))

        temp.sort(key=lambda X: X[1], reverse=True)

        mirrored = 0
        for dict_key, _ in temp:
            tree_counter, key, router = dict_key.split('-')
            cmd += 'q;qnoq' + tree_counter + 'qpermitqipq' + key + router
            mirrored += 1

            if mirrored == 30:
                break

        if mirrored:
            subprocess.run(["sh", "./run_single_cmd.sh", cmd])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--p1', help='prefixes to add R1')
    parser.add_argument('--p2', help='prefixes to add R2')
    parser.add_argument('--p3', help='prefixes to add R3')
    parser.add_argument('--p4', help='prefixes to add R4')
    parser.add_argument('--iter', help='iteration 1 or 2')
    args = parser.parse_args()
    main(args.p1, args.p2, args.p3, args.p4, args.iter)
