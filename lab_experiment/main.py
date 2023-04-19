import pytricia
from util.create_tables_cisco import get_mirrored_table
from util.create_tables_cisco import get_sampled_table
from util.create_tables_cisco import get_size
from util.ip_conversion import ipv4_to_str
from util.find_sentinels import Sentinel
from collections import defaultdict
import subprocess
import time
import pandas as pd
import glob
import os


WAIT_TIME = 15
RULE_LIMIT = 500


def deployment_most_active(found_sentinels, iteration, src_ips):
    tree = pytricia.PyTricia()

    for ip, size, router in found_sentinels:
        prefix = ipv4_to_str(ip)+'/'+str(size)
        tree[prefix] = router

    counts = defaultdict(int)
    for ip in src_ips:
        if ip in tree:
            counts[tree.get_key(ip)] += 1

    if len(counts) != len(found_sentinels):
        print('Did not find the expected amount of active sentinels!!!')

    sentinel_list = [[], [], [], []]
    for key, value in counts.items():
        router = tree[key]
        sentinel_list[router-1].append((key, router, value))

    for i in range(4):
        # no reverse needed as we pop the last element of the list (== biggest activity)
        sentinel_list[i].sort(key=lambda X: X[2])

    total = 0
    sentinels_per_router = [0, 0, 0, 0]
    prefix_lists = [[], [], [], []]
    with open('output_{}_activity.csv'.format(iteration), 'w') as data_out:
        while total < RULE_LIMIT:
            found = False
            for i in range(4):
                if len(sentinel_list[i]):
                    prefix, router, amount = sentinel_list[i].pop()
                    found = True
                    sentinels_per_router[router - 1] += 1
                    total += 1
                    data_out.write('{},{},{}\n'.format(prefix, prefix.split('/')[1], router))
                    for j in range(4):
                        if j == router - 1:
                            continue
                        prefix_lists[j].append(prefix)

            if not found:
                break

    return prefix_lists


def deployment_largest(found_sentinels, iteration):
    sentinel_list = [[], [], [], []]
    for ip, size, router in found_sentinels:
        prefix = ipv4_to_str(ip)+'/'+str(size)
        sentinel_list[router-1].append((prefix, router, size))

    for i in range(4):
        # reverse search needed as we pop the last element from the list (== smallest number = biggest prefix size)
        sentinel_list[i].sort(key=lambda X: X[2], reverse=True)

    total = 0
    sentinels_per_router = [0, 0, 0, 0]
    prefix_lists = [[], [], [], []]
    with open('output_{}_size.csv'.format(iteration), 'w') as data_out:
        while total < RULE_LIMIT:
            found = False
            for i in range(4):
                if len(sentinel_list[i]):
                    prefix, router, size = sentinel_list[i].pop()
                    found = True
                    sentinels_per_router[router - 1] += 1
                    total += 1
                    data_out.write('{},{},{}\n'.format(prefix, size, router))
                    for j in range(4):
                        if j == router - 1:
                            continue
                        prefix_lists[j].append(prefix)

            if not found:
                break

    return prefix_lists


def main():
    main_start = int(time.time())
    current_sflow = ""
    n_mirroring = -1
    iteration = 0
    switch = 1
    pid = 0
    current_iteration_time = 1

    table_n = []
    table_n_1 = []

    time.sleep(WAIT_TIME)

    while iteration != 33:
        iteration_start = time.time()
        print('--- Starting round', iteration, int(time.time()))
        used_sflow = list()

        files = glob.glob('sflow/nfcapd_moved.*')
        latest = max(files, key=os.path.getctime)

        # no new file or only file from previous run
        ts = int(latest.strip().split('.')[-1])
        if ts < main_start or latest == current_sflow:
            time.sleep(WAIT_TIME)
            continue

        # get newest sampled data
        else:
            temp = list()
            if not current_sflow:
                subprocess.run(["sh", "./sflow_conversion.sh", latest])
                in_t, out_t = get_sampled_table("sflow/dummy.csv")
                if len(in_t) > 0:
                    temp = [in_t]
                used_sflow.append(latest)
            else:
                ts_current = int(current_sflow.strip().split('.')[-1])

                for file in files:
                    ts_file = int(file.strip().split('.')[-1])
                    if ts_file > ts_current:
                        used_sflow.append(file)
                        subprocess.run(["sh", "./sflow_conversion.sh", file])
                        in_t, out_t = get_sampled_table("sflow/dummy.csv")

                    if len(in_t) > 0:
                        temp.append(in_t)

            current_sflow = latest

        for file in used_sflow:
            print(file)

        # add mirrored packets (starting at n_mirroring)
        in_t_m, out_t_m, n_new, m_counters = get_mirrored_table("mirrored/dummy.csv", n_mirroring)

        print(n_mirroring, n_new)

        n_mirroring = n_new

        if len(in_t_m):
            temp.append(in_t_m)

        table_n = temp.copy()

        if iteration == 0:
            table_to_use = pd.concat(temp, ignore_index=True)
        else:
            for x in table_n_1:
                temp.append(x)
            table_to_use = pd.concat(temp, ignore_index=True)

        # perform sentinel search
        search = Sentinel(filename='rules')
        search.t_in = table_to_use.copy()
        search.aggregate(['src_ip', 'dst_ip', 'router_ip'], {'pkts': 'sum'})
        found_sentinels = search.find_sentinel(True, 'src_ip', 'check', 'router_ip')
        search.clean()

        prefix_lists = deployment_most_active(found_sentinels, iteration, table_to_use['src_ip'])

        for i in range(4):
            if len(prefix_lists[i]) == 0:
                prefix_lists[i] = '-'

        if iteration == 0:
            activate = 0
        else:
            activate = 1 + ((iteration + 1) % 2)

        print('--- before install', iteration, int(time.time()))

        subprocess.run(["sh", "./provision_mirroring.sh", ','.join(prefix_lists[0]), ','.join(prefix_lists[1]), ','.join(prefix_lists[2]), ','.join(prefix_lists[3]), str(switch), str(activate)])

        print('--- rules activated', iteration, int(time.time()))

        n_mirrored = get_size("mirrored/dummy.csv")
        print('x', n_mirrored)

        # delete rules
        subprocess.run(["sh", "./cmd_del.sh", ','.join(prefix_lists[0]), ','.join(prefix_lists[1]), ','.join(prefix_lists[2]), ','.join(prefix_lists[3]), str(switch), str(activate)])

        print('--- rules deleted', iteration, int(time.time()))

        # we wait for 1min iteration
        diff = int(60 - (time.time() - iteration_start))
        if diff > 0:
            time.sleep(diff)
        print('--- diff time', iteration, diff)

        if switch == 1:
            switch = 2
        else:
            switch = 1

        table_n_1 = table_n.copy()

        # current_iteration_time = int(time.time() - iteration_start)
        iteration += 1


if __name__ == '__main__':
    main()
