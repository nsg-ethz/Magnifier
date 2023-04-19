""" Utility functions for simulations
"""

from common.ip_conversion import ipv4_to_str, ipv4_to_int
from common.find_sentinels import Sentinel
import numpy as np
import pandas as pd
from collections import defaultdict
import pytricia


# no longer used
def prepare_ingress_routers(n):
    """ Prepare values to figure out over which ingress a packet would enter our network

    n (int): number of border router (should be power of two)

    returns: list of start and stop IP values
    """

    boundaries = list()
    total = 2**32
    unit = int(total / n)
    for i in range(n):
        boundaries.append((i*unit, (i+1)*unit))

    return boundaries


# no longer used
def get_router_n(ip, boundaries):
    """ Returns to which ingress a packet belongs in our network

    ip (int): dst IP of packet as int (as we look for do the ingress decision based on dst IP)
    boundaries (list): previously computed values to indicate which router it will be

    returns: ID of router (int from 1 to n)
    """

    router = 1
    for start, end in boundaries:
        if start <= ip < end:
            return router
        router += 1

    print('unexpected IP, could not find ingress', ip)


def get_24_prefixes(prefix):
    """ Returns all the /24 prefixes contained in a given prefix

    prefix (str): prefix in dot notation (e.g., 1.2.0.0/16)

    returns: all /24 prefixes in dot notation
    """

    # iterate current INT value + 256 up to ...
    ip, size = prefix.split('/')
    ip_int = ipv4_to_int(ip)
    prefixes_24 = list()
    for i in range(2**(24-int(size))):
        new_ip = ip_int + i*256
        prefixes_24.append(ipv4_to_str(new_ip)+'/24')

    return prefixes_24


def get_table(pkts):
    """ Returns table useable by sentinel search

    pkts (list):
        list of packets to convert to table

    returns:
        table as pandas dataframe
    """
    new_list = list()
    for src_ip, prefix, router in pkts:
        new_list.append((router, src_ip, 1))

    column_type = [('router_ip', 'uint32'), ('src_ip', 'uint32'),
                   ('pkts', 'uint32')]

    arr = np.array(new_list, dtype=column_type)
    table = pd.DataFrame.from_records(arr)

    return table


def enhance_sentinels(sentinels, pkts):
    """ Enhances sentinels with size and activity counter

    sentinels (list): current sentinels
    pkts (list): pkts of current iteration

    returns
        dict {sentinel: (router, pkt count, size)}
    """

    sentinel_dict = dict()
    tree = pytricia.PyTricia()

    for prefix, router in sentinels:
        _, size = prefix.split('/')
        sentinel_dict[prefix] = [router, 0, int(size)]
        tree[prefix] = router

    for _, prefix, _ in pkts:
        match = tree.get_key(prefix)
        if match:
            sentinel_dict[match][1] += 1

    return sentinel_dict


def order_sentinels(sentinels, criteria):
    """ Orders sentinels based on a criteria

    sentinels (dict): enhanced sentinel dict
    criteria (string): used ordering criteria

    returns
        list (prefix, router) of ordered sentinels in normal format

    """

    temp = list()
    for key, value in sentinels.items():
        temp.append((key, value[0], value[1], value[2]))

    if criteria == 'activity':
        temp.sort(key=lambda X: X[2], reverse=True)
    elif criteria == 'size':
        temp.sort(key=lambda X: X[3])

    ordered = [(sentinel, router) for sentinel, router, _, _ in temp]
    return ordered


def get_sentinels(samples, start, end):
    """ Returns found sentinels

    samples (list);
        list of packets to use for the sentinel search
    start (int):
        sentinel search prefix start size
    end (int):
        sentinel search prefix end size

    returns:
        list (prefix, router) of found sentinels with corresponding router
    """

    # Load samples as dataframe
    table = get_table(samples)

    search = Sentinel()
    search.t_in = table.copy()
    search.aggregate(['src_ip', 'router_ip'], {'pkts': 'sum'})
    found_sentinels = search.sentinel_search(True, 'src_ip', 'check', 'router_ip', start=32-start, end=32-end)
    search.clean()

    # sentinels = list()
    sentinels = set()
    for ip, size, router in found_sentinels:
        prefix = ipv4_to_str(ip)+'/'+str(size)
        sentinels.add((prefix, router))

    return sentinels


def get_result_string(data):
    """ Generates results string for csv

    data (list): list of data points

    returns: comma-separated string with data points
    """

    return ','.join(str(x) for x in data)


def gt_init():
    """ Initialization of ground truth data structure

        returns:
            dict( ingress_router = empty set, pkt_count = 0 )
    """
    return {
        'ingress_router': set(),
        'pkt_count': 0
    }


def get_ground_truth(pkts):
    """ Gets ground truth data

    pkts (list):
        list of packets (in n)

    returns:
        dict of sets (key = /24 prefix, set = observed ingress points)
    """

    gt_data = defaultdict(gt_init)

    for src_ip, prefix, router in pkts:
        gt_data[prefix]['ingress_router'].add(router)
        gt_data[prefix]['pkt_count'] += 1

    return gt_data


def compare_sets(set_new, set_old):
    """Compare elements present, added, and removed between
    two versions of the same set.

    set_new (set):
        new version of a set
    set_old (set):
        old version of a set

    returns:
        n_new (int): number of elements in the new set
        n_added (int): number of elements added in the new set
        n_removed (int): number of elements removed from the old set
    """

    # count items that are no longer in the set
    n_removed = 0
    for item in set_old:
        if item not in set_new:
            n_removed += 1

    # calculate number of new item
    n_new = len(set_new)
    n_old = len(set_old)
    n_added = n_new + n_removed - n_old

    return n_new, n_added, n_removed


def export_sentinels(sentinels, pkts, out_file, iteration):
    """ Exports all found sentinels together with known packet amount

    sentinels (set): sentinels to consider
    pkts (list): list of all pkts the sentinels are based on
    out_file (str): file name to write found sentinels to
    iteration (int): current simulation iteration
    """

    sentinel_dict = enhance_sentinels(sentinels, pkts)

    with open(out_file, 'a') as data_out:
        data_out.write('iteration,{}\n'.format(iteration))
        for key, values in sentinel_dict.items():
            data_out.write('{},{},{}\n'.format(key, values[0], values[1]))
