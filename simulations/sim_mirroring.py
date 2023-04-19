""" Simulation functions related to mirroring
"""

import pytricia
from sim_util import get_sentinels, order_sentinels, enhance_sentinels
import random


def get_mirroring_rules(pkts, sentinel_start, sentinel_end, order, top):
    """ Generates a prefix tree which matches mirroring rules

    pkts (list): 
        list of packets
    sentinel_start (int): 
        sentinel search prefix start size
    sentinel_end (int): 
        sentinel search prefix end size
    order (str):
        ordering criteria
    top (int):
        number of deployed sentinels, set to None to use all of them

    returns: (rules, sentinels)
        rules: pytricia prefix tree matching mirroring rules (value == ingress router)
        sentinels: the computed sentinels
    """
    sentinels = get_sentinels(pkts, sentinel_start, sentinel_end)

    # enhance and order based on top criteria
    if top is not None:
        sentinel_dict = enhance_sentinels(sentinels, pkts)
        ordered_sentinels = order_sentinels(sentinel_dict, order)

        rules = pytricia.PyTricia()
        for prefix, router in ordered_sentinels[0:top]:
            rules[prefix] = router

        return (rules, ordered_sentinels[0:top])

    else:
        rules = pytricia.PyTricia()
        for prefix, router in sentinels:
            rules[prefix] = router

        return (rules, sentinels)


def get_mirrored_packets(rules, pkts, remove_rules):
    """ Returns all mirrored packets given some mirroring rules

    rules (prefix tree): 
        pytricia prefix tree matching mirroring rules (value == ingress router)
    pkts (list): 
        list of packets
    remove_rules (bool):
        remove mirroring rules once they have mirrored first packet

    returns: (mirrored_pkts, removed_sentinels) 
        mirrored_pkts: list (IP, /24 prefix, router) of all mirrored packets
        removed_sentinels: set of removed sentinels
    """

    mirrored_pkts = list()
    removed_sentinels = set()

    for src_ip, prefix, router in pkts:
        # if packet belongs to correct sentinel ingress router, it will *not* be mirrored
        if src_ip in rules and rules[src_ip] != router:
            mirrored_pkts.append((src_ip, prefix, router))

            # note that we currently remove the corresponding mirroring rules on all
            # routers as soon as one rule for a given sentinel starts to mirror
            # if we only want to remove the actual rule which mirrored packets, we would
            # need to start keeping track of rules on each individual device
            if remove_rules:
                sentinel = rules.get_key(src_ip)
                removed_sentinels.add(sentinel)
                del rules[sentinel]

    return (mirrored_pkts, removed_sentinels)


def get_mirrored_packets_everflow(pkts, frequency, flags):
    """ Get sampled packets for everflow

    pkts (list): list of packets
    frequency (int): n for sampling frequency 1/n
    flags (list): list of booleans if packet has flags set 

    returns: list with sampled packets (every nth and TCP SYN,FIN and RST)
    """

    sampled_pkts = list()

    # add all packets with flags
    for i, flag in enumerate(flags):
        if flag:
            sampled_pkts.append(pkts[i])

    # add randomly sampled packets but only if not already covered by flags
    start = random.randrange(0, frequency)
    while start < len(pkts):
        if not flags[start]:
            sampled_pkts.append(pkts[start])
        start += frequency

    return sampled_pkts
