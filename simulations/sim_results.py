""" Result functions for simulations
"""

import pytricia
from sim_util import get_24_prefixes
from collections import defaultdict


def get_total_coverage(all_samples, sentinels):
    """ Gets total coverage of given sentinels and samples

    all_samples (list): 
        all sampled packets
    sentinels (list): 
        list of found sentinels

    returns: (all_24, count_multi)
        all_24: set of all covered /24 prefixes
        count_multi: number of /24 prefixes with sample but no unique sentinel
    """

    all_24 = set()
    for prefix, router in sentinels:
        for prefix_24 in get_24_prefixes(prefix):
            all_24.add(prefix_24)

    if len(all_samples) == 0:
        return all_24

    else:
        all_24_copy = all_24.copy()

        count_multi = 0
        test_dict = defaultdict(int)
        for ip, prefix, router in all_samples:
            if prefix not in all_24_copy:
                all_24.add(prefix)
                test_dict[prefix] += 1

        count_multi = len(test_dict)

        for key, value in test_dict.items():
            # that would mean a /24 prefix with only a single ingress point
            # which the sentinel search did not find. Assuming the sentinel
            # search goes up to /24, that should never happen
            if value <= 1:
                print('!!! unexpected sentinel with multiple entries:', key, value)

        return (all_24, count_multi)


def get_results_sampled(pkts, n_24):
    """ Simulation results using sampled packets only

    pkts (list): 
        all sampled packets
    n_24 (int): 
        total number of covered /24 prefixes by sentinels

    returns: simulation results:
        - number of correct (> 0)
        - number of wrong (always 0)
        - number of uncertain (?) (always 0)
        - number of no traffic (!) (always 0)
        - number of unknown (-) (>0)
    """

    correct = set()
    for ip, prefix, router in pkts:
        correct.add(prefix)

    # correct, wrong, ?, !, -
    return (len(correct), 0, 0, 0, n_24 - len(correct))


def get_results_sentinel_sampling(sentinels, mirrored_pkts, n_multi, all_samples):
    """ Simulation results using sentinels based on sampled packets only

    sentinels (list): 
        list of found sentinels
    mirrored_pkts (list): 
        mirrored packets, used to identify wrong answers
    n_multi (int): 
        amount of /24 prefixes for which it is impossible to find unique sentinels
    all_samples (list): 
        all sampled packets

    returns: simulation results:
        - number of correct (> 0)
        - number of wrong (> 0)
        - number of uncertain (?) (> 0)
        - number of no traffic (!) (always 0)
        - number of unknown (-) (always 0)
    """

    mirrored_set = set()
    for ip, prefix, router in mirrored_pkts:
        mirrored_set.add(prefix)

    mirrored_test_set = mirrored_set.copy()

    sampled_set = set()
    for ip, prefix, router in all_samples:
        sampled_set.add(prefix)

    sampled_test_set = sampled_set.copy()

    correct = 0
    wrong = 0
    uncertain = 0

    for prefix, router in sentinels:
        for prefix_24 in get_24_prefixes(prefix):
            # at least one mirroring rule triggered (wrong inference)
            if prefix_24 in mirrored_set and prefix_24 not in sampled_set:
                wrong += 1
                if prefix_24 in mirrored_test_set:
                    mirrored_test_set.remove(prefix_24)

            # this is the case if we have a mirrored observation but now also a sample in the same /24
            # could e.g., happen if it changed over time
            elif prefix_24 in sampled_set:
                correct += 1
                if prefix_24 in mirrored_test_set:
                    mirrored_test_set.remove(prefix_24)

            # we are uncertain about correctness
            else:
                uncertain += 1

            if prefix_24 in sampled_test_set:
                sampled_test_set.remove(prefix_24)

    # if we remove all the covered samples we should only end up with samples which belong to non-unique sentinels
    if len(sampled_test_set) - n_multi != 0:
        print('unexpected amount of entries which the sentinel algorithm did not cover', len(sampled_test_set), n_multi)

    correct += n_multi

    # correct, wrong, ?, !, -
    return (correct, wrong, uncertain, 0, 0)


def get_results_sentinel_mirroring(sentinels, mirrored_pkts, n_multi, n_24, final_pkts, rules):
    """ Simulation results using sentinels based on sampled packets and newest mirrored packets

    sentinels (list): list of found sentinels
    mirrored_pkts (list): mirrored packets
    n_multi (int): amount of /24 prefixes for which it is impossible to find unique sentinels
    n_24 (int): total number of covered /24 prefixes by sentinels
    final_pkts (list): all sampled and mirrored packets
    rules (prefix tree): mirorring rules based on sentinels

    returns: simulation results:
        - number of correct (> 0)
        - number of wrong (always 0)
        - number of uncertain (?) (> 0)
        - number of no traffic (!) (> 0)
        - number of unknown (-) (should be 0)
    """

    mirrored_set = set()
    for ip, prefix, router in mirrored_pkts:
        mirrored_set.add(prefix)

    # based on mirrored and sampled packets
    known_set = set()
    for ip, prefix, router in final_pkts:
        known_set.add(prefix)

    correct = 0
    no_traffic = 0
    uncertain = 0

    for prefix, router in sentinels:
        for prefix_24 in get_24_prefixes(prefix):

            # sentinel /24 is based on mirrored packet -> correct
            # note that this was mirrored before we activate this sentinel
            if prefix_24 in mirrored_set:
                correct += 1

            # sentinel /24 is based on sampled packet
            # or previously mirrored packet -> correct
            elif prefix_24 in known_set:
                correct += 1

            else:
                # /24 sentinel is covered by currently active mirroring rule
                # but we did not observe any mirrored traffic
                if prefix_24 in rules:
                    no_traffic += 1

                # found /24 sentinel is based on sample of this iteration but we currently
                # do not have an active mirroring rule (will be installed in next iteration)
                # we are uncertain about correctness
                else:
                    uncertain += 1

    correct += n_multi

    # possible unknown, should always be 0
    unknown = n_24 - correct - no_traffic - uncertain
    if unknown != 0:
        print('unknown /24 prefix when considering sentinels based on mirroring, should never happen:', unknown)

    # correct, wrong, ?, !, -
    return (correct, 0, uncertain, no_traffic, unknown)


def get_results_ground_truth(gt_data, sentinels, remove_invalid=False):
    """ Simulation results based on current ground truth data

    gt_data (dict of sets): 
        current ground truth data
    sentinels (list): 
        list of found sentinels
    remove_invalid (bool):
        if True, remove sentinels completely if they are invalid based on ground truth data

    returns: simulation results:
        - number /24 in sentinel and correct ingress based on gt data
        - number /24 in sentinel and wrong ingress based on gt data
        - number /24 in sentinel but not visible in gt data
        - number /24 not in sentinel but visible in gt data
        - number /24 in sentinel which are correct but not unique in gt data (already counted in first entry)
        - number /24 not in sentinel but visible in gt data and not unique (already counted in fourth entry)
        - number of packets with a correct ingress based on gt data
        - pkt count belonging to correctly inferred /24 prefixes
        - pkt count belonging to wrongly inferred /24 prefixes
        - pkt count belonging to covered /24 prefixes which have no unique ingress in gt data
        - pkt count belonging to not covered /24 prefixes which are active in gt data
        - pkt count belonging to not covered /24 prefixes which are active but not unique in gt data
        - pkt count for all packets belonging to unique /24 in gt data
    """

    covered_correct = 0
    pkt_count_correct = 0
    covered_wrong = 0
    covered_not_active = 0
    covered_not_unique = 0
    not_covered = 0
    not_covered_not_unique = 0
    covered_correct_count = 0
    covered_wrong_count = 0
    covered_not_unique_count = 0
    not_covered_count = 0
    not_covered_not_unique_count = 0
    count_all_unique_pkts = 0

    # to keep track of /24 already covered by sentinels
    checked = set()

    if not remove_invalid:
        sentinels_to_analyze = sentinels.copy()
    else:
        sentinels_to_analyze = list()
        for prefix, router in sentinels:
            is_valid = True
            for prefix_24 in get_24_prefixes(prefix):
                if prefix_24 in gt_data:
                    # either the inference is completely wrong
                    # or we have a non unique /24 prefix
                    # -> remove the sentinel completely
                    if router not in gt_data[prefix_24]['ingress_router'] or len(gt_data[prefix_24]['ingress_router']) > 1:
                        is_valid = False
                        break

            if is_valid:
                sentinels_to_analyze.append((prefix, router))

    for prefix, router in sentinels_to_analyze:

        for prefix_24 in get_24_prefixes(prefix):
            checked.add(prefix_24)

            if prefix_24 in gt_data:
                # correctly identified ingress
                if router in gt_data[prefix_24]['ingress_router']:
                    covered_correct += 1
                    covered_correct_count += gt_data[prefix_24]['pkt_count']
                    pkt_count_correct += gt_data[prefix_24]['pkt_count']

                    # but was actually not unique
                    if len(gt_data[prefix_24]['ingress_router']) > 1:
                        covered_not_unique += 1
                        covered_not_unique_count += gt_data[prefix_24]['pkt_count']
                    else:
                        count_all_unique_pkts += gt_data[prefix_24]['pkt_count']

                # wrong inference
                else:
                    covered_wrong += 1
                    covered_wrong_count += gt_data[prefix_24]['pkt_count']

                    if len(gt_data[prefix_24]['ingress_router']) == 1:
                        count_all_unique_pkts += gt_data[prefix_24]['pkt_count']

            # covered by sentinel but not in ground truth data
            else:
                covered_not_active += 1

    for key, value in gt_data.items():
        if key not in checked:
            # not covered by sentinel but active in ground truth data
            not_covered += 1
            not_covered_count += value['pkt_count']

            # not covered by sentinel but difficult to find as not unique
            if len(value['ingress_router']) > 1:
                not_covered_not_unique += 1
                not_covered_not_unique_count += value['pkt_count']
            else:
                count_all_unique_pkts += value['pkt_count']

    # if we do not need "checked", we can compute not covered as:
    # not_covered = len(gt_data) - correct - wrong

    return (
        covered_correct,
        covered_wrong,
        covered_not_active,
        not_covered,
        covered_not_unique,
        not_covered_not_unique,
        pkt_count_correct,
        covered_correct_count,
        covered_wrong_count,
        covered_not_unique_count,
        not_covered_count,
        not_covered_not_unique_count,
        count_all_unique_pkts,
    )


def get_results_ground_truth_sampling(gt_data, samples):
    """ Simulation results based on current ground truth data
        if we consider sampling only

    gt_data (dict of sets): 
        current ground truth data
    samples (list): 
        list of sampled packets

    returns: simulation results:
        - number /24 prefixes covered
        - number /24 prefixes covered not unique
        - number /24 prefixes not covered
        - number /24 prefixes not covered not unique
        - number pkts covered
        - number pkts covered not unique
        - number pkts not covered
        - number pkts not covered not unique
        - number /24 prefixes which are no longer active in ground truth data
    """

    set_covered = set()
    set_not_active = set()
    pkt_counter_covered = 0
    counter_not_unique = 0
    pkt_counter_not_unique = 0
    counter_not_covered = 0
    counter_not_covered_not_unique = 0
    pkt_counter_not_covered = 0
    pkt_counter_not_covered_not_unique = 0
    counter_not_active = 0

    for sample in samples:
        # get sample's prefix
        prefix = sample[1]

        # Given that ground truth and sampled packets are based on the same
        # input data, we do not have to compare the actual ingress router.
        # The sampled packet will always enter over one of the ingress routers
        # assigned to the corresponding /24 prefix in the ground truth data.
        if prefix not in set_covered and prefix not in set_not_active:
            # check if prefix is still active in current ground truth data
            if prefix in gt_data:
                # add the sample's prefix to the covered set
                set_covered.add(prefix)
                # count the corresponding packets
                pkt_counter_covered += gt_data[prefix]['pkt_count']
            else:
                # make sure we count it only once as not active
                set_not_active.add(prefix)
                counter_not_active += 1

    for prefix in set_covered:
        if prefix in gt_data and len(gt_data[prefix]['ingress_router']) > 1:
            counter_not_unique += 1
            pkt_counter_not_unique += gt_data[prefix]['pkt_count']

    for prefix, value in gt_data.items():
        if prefix not in set_covered:
            counter_not_covered += 1
            pkt_counter_not_covered += value['pkt_count']
            if len(value['ingress_router']) > 1:
                counter_not_covered_not_unique += 1
                pkt_counter_not_covered_not_unique += value['pkt_count']

    return (
        len(set_covered),                    # nb. of prefixes covered
        counter_not_unique,                  # nb. of these prefixes that have more than one ingress point
        counter_not_covered,                 # nb. of prefixes not covered
        counter_not_covered_not_unique,      # nb. of prefixes not covered which are not unique
        pkt_counter_covered,                 # nb. of packets covered
        pkt_counter_not_unique,              # nb. of packets covered with non-unique ingress point
        pkt_counter_not_covered,             # nb. of packets not covered
        pkt_counter_not_covered_not_unique,  # nb. of packets not covered which non-unique ingress point
        counter_not_active,                  # nb. of prefixes which are no longer active in gt data
    )


def get_results_ground_truth_invalidated_sentinels(sentinels, removed_sentinels, gt_data):
    """ Simulation results for the sentinels which got invalidated by the
        deployed mirroring rules

    sentinels (list):
        list of current sentinels
    removed_sentinels (set):
        set of removed sentinels due to mirroring
    gt_data (dict of sets):
        current ground truth data

    returns: (sentinels, results)
        sentinels: all sentinels which are still valid
        results (list):
            - number /24 prefixes lost due to invalid sentinels
            - number /24 prefixes lost due to invalid sentinels which are not unique in gt data
            - number /24 prefixes lost due to invlaid sentinels which are not active in gt data
            - number pkts lost due to invalid sentinels
            - number pkts lost due to invalid sentinels which are not unique
    """

    prefix_lost = 0
    prefix_lost_not_unique = 0
    prefix_lost_not_active = 0
    pkt_lost = 0
    pkt_lost_not_unique = 0

    for prefix in removed_sentinels:
        # given that sentinels do not overlap, we do not need
        # to check if we already covered this case
        for prefix_24 in get_24_prefixes(prefix):
            if prefix_24 in gt_data:
                prefix_lost += 1
                pkt_lost += gt_data[prefix_24]['pkt_count']

                if len(gt_data[prefix_24]['ingress_router']) > 1:
                    prefix_lost_not_unique += 1
                    pkt_lost_not_unique += gt_data[prefix_24]['pkt_count']

            else:
                prefix_lost_not_active += 1

    still_valid_sentinels = list()
    for prefix, router in sentinels:
        if prefix not in removed_sentinels:
            still_valid_sentinels.append((prefix, router))

    return (still_valid_sentinels,
            (
                prefix_lost,
                prefix_lost_not_unique,
                prefix_lost_not_active,
                pkt_lost,
                pkt_lost_not_unique
            ))
