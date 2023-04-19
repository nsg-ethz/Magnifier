""" Main functions for simulations
"""

import argparse
import random
import os.path
import sys

from sim_util import get_result_string, get_ground_truth, compare_sets
from sim_pkts import get_sampled_packets_per_router, get_sampled_packets_everflow, get_preprocessed_pkts, prepare_permutations, get_preprocessed_pkts_mapping
from sim_mirroring import get_mirroring_rules, get_mirrored_packets
from sim_results import get_results_ground_truth, get_results_ground_truth_sampling, get_results_ground_truth_invalidated_sentinels
from sim_util import get_sentinels

from common.helpers import setup_logging

import logging
log = logging.getLogger(__name__)


prefix_file = '../input_data/all_prefixes.txt'

# set random seed for simulations
# influences which packets are sampled
random.seed('new sim')

# Parameters for top k analysis
TOP_K = [100, 500, 1000, 5000]
ORDERING = ['activity', 'size', 'full']

default_results_magnifier = [
    'n_total_packets',
    'n_prefixes',
    'max_pkt_router',
    'min_pkt_router',
    'iteration_end_ts',
]

default_results_everflow = [
    'n_mirrored_packets',
    'n_flag_packets',
    'n_random_packets',
    'n_total_packets',
    'n_prefixes',
    'max_pkt_router',
    'min_pkt_router',
    'iteration_end_ts',
    'n_sentinels_total',
    'n_sentinels_added',
    'n_sentinels_removed',
]

results_sampling_only = [
    'prefix_correct_sampling',
    'prefix_covered_not_unique_sampling',
    'prefix_not_covered_sampling',
    'prefix_not_covered_not_unique_sampling',
    'pkt_covered_correct_sampling',
    'pkt_covered_correct_not_unique_sampling',
    'pkt_not_covered_sampling',
    'pkt_not_covered_not_unique_sampling',
    'prefix_not_active_sampling',
]

results_sentinel_without_mirroring = [
    'prefix_correct_sentinel',
    'prefix_wrong_sentinel',
    'prefix_not_active_sentinel',
    'prefix_not_covered_sentinel',
    'prefix_covered_not_unique_sentinel',
    'prefix_not_covered_not_unique_sentinel',
    'pkt_covered_correct_sentinel',
    'pkt_covered_wrong_sentinel',
    'pkt_covered_not_unique_sentinel',
    'pkt_not_covered_sentinel',
    'pkt_not_covered_not_unique_sentinel',
    'pkt_all_unique_sentinel',
    'prefix_correct_sentinel_old',
    'prefix_wrong_sentinel_old',
    'prefix_not_active_sentinel_old',
    'prefix_not_covered_sentinel_old',
    'prefix_covered_not_unique_sentinel_old',
    'prefix_not_covered_not_unique_sentinel_old',
    'pkt_covered_correct_sentinel_old',
    'pkt_covered_wrong_sentinel_old',
    'pkt_covered_not_unique_sentinel_old',
    'pkt_not_covered_sentinel_old',
    'pkt_not_covered_not_unique_sentinel_old',
    'pkt_all_unique_sentinel_old',
]

magnifier_results_sentinel_with_mirroring = [
    'n_sentinels_total_mirroring',
    'n_sentinels_added_mirroring',
    'n_sentinels_removed_mirroring',
    'n_mirrored_packets_mirroring',
    'prefix_correct_mirroring',
    'prefix_wrong_mirroring',
    'prefix_not_active_mirroring',
    'prefix_not_covered_mirroring',
    'prefix_covered_not_unique_mirroring',
    'prefix_not_covered_not_unique_mirroring',
    'pkt_covered_correct_mirroring',
    'pkt_covered_wrong_mirroring',
    'pkt_covered_not_unique_mirroring',
    'pkt_not_covered_mirroring',
    'pkt_not_covered_not_unique_mirroring',
    'n_sentinels_invalidated_mirroring',
    'prefix_lost_mirroring',
    'prefix_lost_not_unique_mirroring',
    'prefix_lost_not_active_mirroring',
    'pkt_lost_mirroring',
    'pkt_lost_not_unique_mirroring',
]


def make_sim_magnifier(in_file, out_file, frequency, duration, pps,
                       s_start, s_end, iteration, border, use_persistent,
                       permutation):
    """ main simulation function

    in_file (str): 
        filename to file with parsed packet information
    out_file (str): 
        name of file with results
    frequency (int): 
        sampling frequency n -> every n-th packet is sampled
    duration (int): 
        how long one iteration takes in seconds
    pps (int): 
        number of replayed packets per second (-1 == real replay speed)
    s_start (int):
        sentinel search prefix start size
    s_end (int): 
        sentinel search prefix end size
    iteration (int): 
        number of simulation iterations
    border (int): 
        number of border routers to consider
    permutation (int):
        percentage of permutations, -1 means not used
    """

    # create permutations if needed
    if permutation != -1:
        mapping = prepare_permutations(permutation, prefix_file, border)

    # helper - replay_real_speed
    if pps == -1:
        replay_real_speed = True
    else:
        replay_real_speed = False

    # sampled and mirrored packets of previous iterations
    mirrored_pkts = []
    mirrored_pkts_n_1 = []
    mirrored_pkts_n_2 = []
    sampled_pkts = []
    sampled_pkts_n_1 = []
    sampled_pkts_n_2 = []
    sentinels_with_mirroring = []
    sentinels_with_mirroring_n_1 = []

    for order in ORDERING:
        if order != 'full':
            for top in TOP_K:
                mirrored_pkts.append([])
                mirrored_pkts_n_1.append([])
                mirrored_pkts_n_2.append([])
                sentinels_with_mirroring.append({})
                sentinels_with_mirroring_n_1.append({})

        # for run with all sentinels
        else:
            mirrored_pkts.append([])
            mirrored_pkts_n_1.append([])
            mirrored_pkts_n_2.append([])
            sentinels_with_mirroring.append({})
            sentinels_with_mirroring_n_1.append({})

    # prepare lists to save various results of each iteration
    result_dict = dict()
    for name in default_results_magnifier:
        result_dict[name] = list()

    # top k sentinels do not have an influence on results based on sampling only
    for name in results_sampling_only:
        result_dict['full_{}'.format(name)] = list()

    # top k sentinels do not have an influence on results based on sentinels without mirroring
    for name in results_sentinel_without_mirroring:
        result_dict['full_{}'.format(name)] = list()

    # top k sentinels do influence the results based on sentinels with mirroring
    for name in magnifier_results_sentinel_with_mirroring:
        for order in ORDERING:
            if order != 'full':
                for top in TOP_K:
                    result_dict['top_{}_{}_{}'.format(top, order, name)] = list()

            # for case with unlimited number of mirroring rules
            else:
                result_dict['full_{}'.format(name)] = list()

    # preparations for reading packets in
    file_ptr = open(in_file, 'r')

    # prepare sampling start points once
    sampling_progress = list()
    for i in range(border):
        sampling_progress.append(random.randrange(0, frequency))

    # main loop
    for i in range(iteration):
        log.info("Iteration {}... (magnifier)".format(i))

        # prepare this iteration
        # moved to the top to support continue statements
        # order is important, do not change
        # sampled packets do not depend on the top k analysis
        sampled_pkts_n_2 = sampled_pkts_n_1
        sampled_pkts_n_1 = sampled_pkts

        # mirrored packets (and sentinels) need to be stored for each top k case
        i_top = 0
        for order in ORDERING:
            if order != 'full':
                for top in TOP_K:
                    mirrored_pkts_n_2[i_top] = mirrored_pkts_n_1[i_top]
                    mirrored_pkts_n_1[i_top] = mirrored_pkts[i_top]
                    sentinels_with_mirroring_n_1[i_top] = sentinels_with_mirroring[i_top]
                    i_top += 1

            # for run with all sentinels
            else:
                mirrored_pkts_n_2[i_top] = mirrored_pkts_n_1[i_top]
                mirrored_pkts_n_1[i_top] = mirrored_pkts[i_top]
                sentinels_with_mirroring_n_1[i_top] = sentinels_with_mirroring[i_top]

        # get iteration end points
        if replay_real_speed:
            start = i     * duration  # time
            end   = (i+1) * duration  # time
        else:
            start = i     * duration * pps    # pkt numb
            end   = (i+1) * duration * pps    # pkt numb

        # all packets which belong to the current iteration
        if permutation != -1:
            current_pkts, timestamps, _, file_ptr, router_pkts, router_flags = get_preprocessed_pkts_mapping(
                file_ptr,
                start,
                end,
                replay_real_speed,
                border,
                mapping,
                time_persistent=use_persistent
            )
        else:
            current_pkts, timestamps, _, file_ptr, router_pkts, router_flags = get_preprocessed_pkts(
                file_ptr,
                start,
                end,
                replay_real_speed,
                border,
                time_persistent=use_persistent
            )

        # we did not find any packets
        # => we reached the end of the trace
        if len(current_pkts) == 0:
            break

        # get sampled packets
        sampled_pkts, sampling_progress = get_sampled_packets_per_router(
            router_pkts,
            router_flags,
            False,
            frequency,
            sampling_progress
        )

        # first iteration, we only have sampled packets
        if i == 0:
            continue

        # real run, compute evaluation results
        # we first handle everything which is unrelated to mirroring
        # and therefore unrelated to the top k analysis
        if i >= 3:
            # get ground truth data based on all packets in n
            gt_data = get_ground_truth(current_pkts)

            temp_length = [len(per_router) for per_router in router_pkts]

            # store results
            # ... min and max packets per router in this iteration
            result_dict['max_pkt_router'].append(max(temp_length))
            result_dict['min_pkt_router'].append(min(temp_length))

            # get number of prefixes and packets in the ground truth
            n_prefixes = len(gt_data)

            # ... number of packets overall
            result_dict['n_total_packets'].append(len(current_pkts))

            # ... maximal number of prefixes coverable
            result_dict['n_prefixes'].append(n_prefixes)

            # ... iteration timestamp
            result_dict['iteration_end_ts'].append(timestamps[-1])

            # full run
            suffix = 'full_'

            # if we consider ground truth-based sampling only evaluation
            # we only take the samples from the current iteration
            results_gt_sampling = get_results_ground_truth_sampling(gt_data, sampled_pkts)

            result_dict[suffix+'prefix_correct_sampling'].append(results_gt_sampling[0])
            result_dict[suffix+'prefix_covered_not_unique_sampling'].append(results_gt_sampling[1])
            result_dict[suffix+'prefix_not_covered_sampling'].append(results_gt_sampling[2])
            result_dict[suffix+'prefix_not_covered_not_unique_sampling'].append(results_gt_sampling[3])
            result_dict[suffix+'pkt_covered_correct_sampling'].append(results_gt_sampling[4])
            result_dict[suffix+'pkt_covered_correct_not_unique_sampling'].append(results_gt_sampling[5])
            result_dict[suffix+'pkt_not_covered_sampling'].append(results_gt_sampling[6])
            result_dict[suffix+'pkt_not_covered_not_unique_sampling'].append(results_gt_sampling[7])
            result_dict[suffix+'prefix_not_active_sampling'].append(results_gt_sampling[8])

            # all samples
            all_samples = (
                sampled_pkts_n_2 +
                sampled_pkts_n_1 +
                sampled_pkts
            )

            # sentinels based on all sampled packets only
            # for now we consider all samples from n, n-1 and n-2
            sentinels_all_samples = get_sentinels(all_samples, s_start, s_end)

            # if we consider ground truth-based sentinel evaluation without mirroring (on a per /24 basis)
            results_gt_sentinel = get_results_ground_truth(gt_data, sentinels_all_samples)

            # ... updating result variables
            result_dict[suffix+'prefix_correct_sentinel_old'].append(results_gt_sentinel[0])
            result_dict[suffix+'prefix_wrong_sentinel_old'].append(results_gt_sentinel[1])
            result_dict[suffix+'prefix_not_active_sentinel_old'].append(results_gt_sentinel[2])
            result_dict[suffix+'prefix_not_covered_sentinel_old'].append(results_gt_sentinel[3])
            result_dict[suffix+'prefix_covered_not_unique_sentinel_old'].append(results_gt_sentinel[4])
            result_dict[suffix+'prefix_not_covered_not_unique_sentinel_old'].append(results_gt_sentinel[5])
            result_dict[suffix+'pkt_covered_correct_sentinel_old'].append(results_gt_sentinel[7])
            result_dict[suffix+'pkt_covered_wrong_sentinel_old'].append(results_gt_sentinel[8])
            result_dict[suffix+'pkt_covered_not_unique_sentinel_old'].append(results_gt_sentinel[9])
            result_dict[suffix+'pkt_not_covered_sentinel_old'].append(results_gt_sentinel[10])
            result_dict[suffix+'pkt_not_covered_not_unique_sentinel_old'].append(results_gt_sentinel[11])
            result_dict[suffix+'pkt_all_unique_sentinel_old'].append(results_gt_sentinel[12])

            # if we consider ground truth-based sentinel evaluation without mirroring (only valid ones)
            results_gt_sentinel = get_results_ground_truth(gt_data, sentinels_all_samples, True)

            # ... updating result variables
            result_dict[suffix+'prefix_correct_sentinel'].append(results_gt_sentinel[0])
            result_dict[suffix+'prefix_wrong_sentinel'].append(results_gt_sentinel[1])
            result_dict[suffix+'prefix_not_active_sentinel'].append(results_gt_sentinel[2])
            result_dict[suffix+'prefix_not_covered_sentinel'].append(results_gt_sentinel[3])
            result_dict[suffix+'prefix_covered_not_unique_sentinel'].append(results_gt_sentinel[4])
            result_dict[suffix+'prefix_not_covered_not_unique_sentinel'].append(results_gt_sentinel[5])
            result_dict[suffix+'pkt_covered_correct_sentinel'].append(results_gt_sentinel[7])
            result_dict[suffix+'pkt_covered_wrong_sentinel'].append(results_gt_sentinel[8])
            result_dict[suffix+'pkt_covered_not_unique_sentinel'].append(results_gt_sentinel[9])
            result_dict[suffix+'pkt_not_covered_sentinel'].append(results_gt_sentinel[10])
            result_dict[suffix+'pkt_not_covered_not_unique_sentinel'].append(results_gt_sentinel[11])
            result_dict[suffix+'pkt_all_unique_sentinel'].append(results_gt_sentinel[12])

        # now we handle everything related to mirroring
        # part of the following code also needs to be done for i == 1 and i == 2 to prepare packet history

        # prepare values to use in final loop
        order_values = list()
        top_values = list()
        suffixes = list()

        for order in ORDERING:
            if order != 'full':
                for top in TOP_K:
                    suffixes.append('top_{}_{}_'.format(top, order))
                    top_values.append(top)
                    order_values.append(order)

            else:
                suffixes.append('full_')
                top_values.append(None)
                order_values.append(None)

        # perform final loop
        for i_top, suffix in enumerate(suffixes):

            # assemble packet history
            # variables are initialized with empty lists
            # -> correct history for i == 1 or i == 2
            pkt_history = (
                sampled_pkts_n_1 +
                sampled_pkts_n_2 +
                mirrored_pkts_n_1[i_top] +
                mirrored_pkts_n_2[i_top]
            )

            # compute sentinels and matching mirroring rules
            rules, found_sentinels = get_mirroring_rules(pkt_history, s_start, s_end, order_values[i_top], top_values[i_top])
            sentinels_with_mirroring[i_top] = found_sentinels

            # get mirrored packets
            mirrored_pkts[i_top], removed_sentinels = get_mirrored_packets(
                rules,
                current_pkts,
                True
            )

            # first real run, compute evaluation results
            if i >= 3:
                # output number of mirrored packets
                result_dict[suffix+'n_mirrored_packets_mirroring'].append(len(mirrored_pkts[i_top]))

                # compute "old" sentinel statistics
                n_sentinels_total, n_sentinels_added, n_sentinels_removed = compare_sets(
                    sentinels_with_mirroring[i_top],
                    sentinels_with_mirroring_n_1[i_top]
                )

                # output sentinel statistic results
                result_dict[suffix+'n_sentinels_total_mirroring'].append(n_sentinels_total)
                result_dict[suffix+'n_sentinels_added_mirroring'].append(n_sentinels_added)
                result_dict[suffix+'n_sentinels_removed_mirroring'].append(n_sentinels_removed)

                # get still valid sentinels and results due to invalid sentinels
                final_sentinels, results_lost = get_results_ground_truth_invalidated_sentinels(
                    sentinels_with_mirroring[i_top],
                    removed_sentinels,
                    gt_data
                )

                # output all results based on lost sentinels
                result_dict[suffix+'n_sentinels_invalidated_mirroring'].append(len(sentinels_with_mirroring[i_top]) - len(final_sentinels))
                result_dict[suffix+'prefix_lost_mirroring'].append(results_lost[0])
                result_dict[suffix+'prefix_lost_not_unique_mirroring'].append(results_lost[1])
                result_dict[suffix+'prefix_lost_not_active_mirroring'].append(results_lost[2])
                result_dict[suffix+'pkt_lost_mirroring'].append(results_lost[3])
                result_dict[suffix+'pkt_lost_not_unique_mirroring'].append(results_lost[4])

                # output results based on ground truth-based evaluation
                # for sentinels with mirroring data which are still valid
                results_gt_mirroring = get_results_ground_truth(
                    gt_data,
                    final_sentinels
                )

                result_dict[suffix+'prefix_correct_mirroring'].append(results_gt_mirroring[0])
                result_dict[suffix+'prefix_wrong_mirroring'].append(results_gt_mirroring[1])
                result_dict[suffix+'prefix_not_active_mirroring'].append(results_gt_mirroring[2])
                result_dict[suffix+'prefix_not_covered_mirroring'].append(results_gt_mirroring[3])
                result_dict[suffix+'prefix_covered_not_unique_mirroring'].append(results_gt_mirroring[4])
                result_dict[suffix+'prefix_not_covered_not_unique_mirroring'].append(results_gt_mirroring[5])
                result_dict[suffix+'pkt_covered_correct_mirroring'].append(results_gt_mirroring[7])
                result_dict[suffix+'pkt_covered_wrong_mirroring'].append(results_gt_mirroring[8])
                result_dict[suffix+'pkt_covered_not_unique_mirroring'].append(results_gt_mirroring[9])
                result_dict[suffix+'pkt_not_covered_mirroring'].append(results_gt_mirroring[10])
                result_dict[suffix+'pkt_not_covered_not_unique_mirroring'].append(results_gt_mirroring[11])

    # adjust iteration end times to end timestamp of first iteration
    temp = result_dict['iteration_end_ts'][0]
    for i in range(len(result_dict['iteration_end_ts'])):
        result_dict['iteration_end_ts'][i] -= temp

    # close pkt input file
    file_ptr.close()

    # write results to file
    with open(out_file, 'w') as data_out:
        for key, values in result_dict.items():
            data_out.write('{},{}\n'.format(key, get_result_string(values)))


def make_sim_everflow(in_file, out_file, frequency, duration, pps,
                      s_start, s_end, iteration, border, use_persistent,
                      permutation):
    """ main simulation function

    in_file (str): filename to file with parsed packet information
    out_file (str): name of file with results
    frequency (int): everflow sampling frequency n -> every n-th packet is sampled
    duration (int): how long one iteration takes in seconds
    pps (int): pps of replayed packets per second (-1 == real replay speed)
    s_start (int): sentinel search prefix start size
    s_end (int): sentinel search prefix end size
    iteration (int): number of simulation iterations
    border (int): number of border routers to consider
    permutation (int): percentage of permutations, -1 means not used
    """

    # create permutations if needed
    if permutation != -1:
        mapping = prepare_permutations(permutation, prefix_file, border)

    # helper - replay_real_speed
    if pps == -1:
        replay_real_speed = True
    else:
        replay_real_speed = False

    # preparations for reading packets in
    file_ptr = open(in_file, 'r')

    # prepare sampling start points once
    sampling_progress = list()
    for i in range(border):
        sampling_progress.append(random.randrange(0, frequency))

    # to save sampled packets of previous iterations
    mirrored_pkts_n_1 = []
    mirrored_pkts_n_2 = []
    mirrored_pkts = []
    sentinels_all_samples = {}

    # prepare lists to save various results of each iteration
    result_dict = dict()
    for name in default_results_everflow:
        result_dict[name] = list()

    # currently we only consider a full run for Everflow
    # top k runs do not make sense
    dynamic_everflow = ['full']

    for name in results_sampling_only:
        for value in dynamic_everflow:
            result_dict['{}_{}'.format(value, name)] = list()
    for name in results_sentinel_without_mirroring:
        for value in dynamic_everflow:
            result_dict['{}_{}'.format(value, name)] = list()

    for i in range(iteration):
        log.info("Iteration {}... (everflow)".format(i))

        # prepare this iteration
        # moved to the top to support continue statements
        # order is important, do not change
        mirrored_pkts_n_2 = mirrored_pkts_n_1
        mirrored_pkts_n_1 = mirrored_pkts
        sentinels_samples_only_n_1 = sentinels_all_samples

        # get iteration end points
        if replay_real_speed:
            start = i     * duration  # time
            end   = (i+1) * duration  # time
        else:
            start = i     * duration * pps    # pkt numb
            end   = (i+1) * duration * pps    # pkt numb

        # all packets which belong to the current iteration
        if permutation != -1:
            current_pkts, timestamps, current_flags, file_ptr, router_pkts, router_flags = get_preprocessed_pkts_mapping(
                file_ptr,
                start,
                end,
                replay_real_speed,
                border,
                mapping,
                time_persistent=use_persistent
            )
        else:
            current_pkts, timestamps, current_flags, file_ptr, router_pkts, router_flags = get_preprocessed_pkts(
                file_ptr,
                start,
                end,
                replay_real_speed,
                border,
                time_persistent=use_persistent
            )

        # we did not find any packets
        if len(current_pkts) == 0:
            break

        # get mirrored packets (== samples)
        mirrored_pkts, sampling_progress, n_flags, n_random = get_sampled_packets_everflow(
            current_pkts,
            current_flags,
            router_pkts,
            router_flags,
            frequency,
            sampling_progress
        )

        # we would already be ready at i == 2 but we only start in interation i == 3
        # to have comparable results with Magnifier
        # results start at i == 3
        if i < 3:
            continue

        result_dict['n_total_packets'].append(len(current_pkts))
        result_dict['n_mirrored_packets'].append(len(mirrored_pkts))
        result_dict['n_flag_packets'].append(n_flags)
        result_dict['n_random_packets'].append(n_random)
        result_dict['iteration_end_ts'].append(timestamps[-1])

        temp_length = [len(per_router) for per_router in router_pkts]
        result_dict['max_pkt_router'].append(max(temp_length))
        result_dict['min_pkt_router'].append(min(temp_length))

        # get ground truth data based on all packets in n
        gt_data = get_ground_truth(current_pkts)

        # get number of prefixes and packets in the ground truth
        n_prefixes = len(gt_data)
        result_dict['n_prefixes'].append(n_prefixes)

        # full run
        suffix = 'full_'

        # results if we consider ground truth-based sampling evaluation
        # we only consider sampled (mirrored in the case of Everflow) packets from the current iteration
        results_gt_sampling = get_results_ground_truth_sampling(gt_data, mirrored_pkts)

        result_dict[suffix+'prefix_correct_sampling'].append(results_gt_sampling[0])
        result_dict[suffix+'prefix_covered_not_unique_sampling'].append(results_gt_sampling[1])
        result_dict[suffix+'prefix_not_covered_sampling'].append(results_gt_sampling[2])
        result_dict[suffix+'prefix_not_covered_not_unique_sampling'].append(results_gt_sampling[3])
        result_dict[suffix+'pkt_covered_correct_sampling'].append(results_gt_sampling[4])
        result_dict[suffix+'pkt_covered_correct_not_unique_sampling'].append(results_gt_sampling[5])
        result_dict[suffix+'pkt_not_covered_sampling'].append(results_gt_sampling[6])
        result_dict[suffix+'pkt_not_covered_not_unique_sampling'].append(results_gt_sampling[7])
        result_dict[suffix+'prefix_not_active_sampling'].append(results_gt_sampling[8])

        # all sampled (mirrored) packets from n, n-1 and n-2
        all_samples = mirrored_pkts_n_1 + mirrored_pkts_n_2 + mirrored_pkts

        # compute sentinels based on all sampled (mirrored) packets
        # for everflow it does not make sense to distinguish between top k cases
        # as we anyway do not deploy and mirroring rules
        sentinels_all_samples = get_sentinels(all_samples, s_start, s_end)

        n_sentinels_total, n_sentinels_added, n_sentinels_removed = compare_sets(
            sentinels_all_samples,
            sentinels_samples_only_n_1
        )

        result_dict['n_sentinels_total'].append(n_sentinels_total)
        result_dict['n_sentinels_added'].append(n_sentinels_added)
        result_dict['n_sentinels_removed'].append(n_sentinels_removed)

        # results if we consider ground truth-based sentinel evaluation (we count on a per /24 basis)
        results_gt_sentinel = get_results_ground_truth(gt_data, sentinels_all_samples)

        result_dict[suffix+'prefix_correct_sentinel_old'].append(results_gt_sentinel[0])
        result_dict[suffix+'prefix_wrong_sentinel_old'].append(results_gt_sentinel[1])
        result_dict[suffix+'prefix_not_active_sentinel_old'].append(results_gt_sentinel[2])
        result_dict[suffix+'prefix_not_covered_sentinel_old'].append(results_gt_sentinel[3])
        result_dict[suffix+'prefix_covered_not_unique_sentinel_old'].append(results_gt_sentinel[4])
        result_dict[suffix+'prefix_not_covered_not_unique_sentinel_old'].append(results_gt_sentinel[5])
        result_dict[suffix+'pkt_covered_correct_sentinel_old'].append(results_gt_sentinel[7])
        result_dict[suffix+'pkt_covered_wrong_sentinel_old'].append(results_gt_sentinel[8])
        result_dict[suffix+'pkt_covered_not_unique_sentinel_old'].append(results_gt_sentinel[9])
        result_dict[suffix+'pkt_not_covered_sentinel_old'].append(results_gt_sentinel[10])
        result_dict[suffix+'pkt_not_covered_not_unique_sentinel_old'].append(results_gt_sentinel[11])
        result_dict[suffix+'pkt_all_unique_sentinel_old'].append(results_gt_sentinel[12])

        # results if we consider ground truth-based sentinel evaluation (invalid sentinels are removed completely)
        results_gt_sentinel = get_results_ground_truth(gt_data, sentinels_all_samples, True)

        result_dict[suffix+'prefix_correct_sentinel'].append(results_gt_sentinel[0])
        result_dict[suffix+'prefix_wrong_sentinel'].append(results_gt_sentinel[1])
        result_dict[suffix+'prefix_not_active_sentinel'].append(results_gt_sentinel[2])
        result_dict[suffix+'prefix_not_covered_sentinel'].append(results_gt_sentinel[3])
        result_dict[suffix+'prefix_covered_not_unique_sentinel'].append(results_gt_sentinel[4])
        result_dict[suffix+'prefix_not_covered_not_unique_sentinel'].append(results_gt_sentinel[5])
        result_dict[suffix+'pkt_covered_correct_sentinel'].append(results_gt_sentinel[7])
        result_dict[suffix+'pkt_covered_wrong_sentinel'].append(results_gt_sentinel[8])
        result_dict[suffix+'pkt_covered_not_unique_sentinel'].append(results_gt_sentinel[9])
        result_dict[suffix+'pkt_not_covered_sentinel'].append(results_gt_sentinel[10])
        result_dict[suffix+'pkt_not_covered_not_unique_sentinel'].append(results_gt_sentinel[11])
        result_dict[suffix+'pkt_all_unique_sentinel'].append(results_gt_sentinel[12])


    # adjust iteration end times to timestamp of first one
    temp = result_dict['iteration_end_ts'][0]
    for i in range(len(result_dict['iteration_end_ts'])):
        result_dict['iteration_end_ts'][i] -= temp

    # close pkt input file
    file_ptr.close()

    # write results to file
    with open(out_file, 'w') as data_out:
        for key, values in result_dict.items():
            data_out.write('{},{}\n'.format(key, get_result_string(values)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--pkts', default='../input_data/simulation_input.csv', type=str,
                        help='file which contains required pkt information generated from pcap')
    parser.add_argument('-o', '--outfile', default='test_run.csv', type=str,
                        help='filename to save results')
    parser.add_argument('-f', '--frequency', default=1024, type=int,
                        help='sampling frequency')
    parser.add_argument('-d', '--duration', default=30, type=int,
                        help='duration of one iteration in seconds')
    parser.add_argument('-P', '--pps', default=-1, type=int,
                        help='number of replayed pkts/sec (-1 == real speed)')
    parser.add_argument('-s', '--start', default=16, type=int,
                        help='sentinel search prefix start size')
    parser.add_argument('-e', '--end', default=24, type=int,
                        help='sentinel search prefix end size')
    parser.add_argument('-i', '--iteration', default=20, type=int,
                        help='number of iterations, after bootstrap')
    parser.add_argument('-m', '--magnifier', default=1, type=int,
                        help='use magnifier (1) or everflow (0)')
    parser.add_argument('-b', '--border', default=4, type=int,
                        help='number of border routers to consider')
    parser.add_argument('-t', '--traffic', default=1, type=int,
                        help='pkt to border mapping in the best (1, default) or worst (0) way')
    parser.add_argument('-a', '--amount', default=-1, type=int,
                        help='percentage of permutations (0..100), default -1')
    parser.add_argument(
        "-v",
        "--verbose",
        dest="loglevel",
        help="set loglevel to INFO",
        action="store_const",
        const=logging.INFO)
    parser.add_argument(
        "-vv",
        "--very-verbose",
        dest="loglevel",
        help="set loglevel to DEBUG",
        action="store_const",
        const=logging.DEBUG)

    args = parser.parse_args()
    setup_logging(args.loglevel)

    # some argument sanity checks
    if not os.path.exists(args.pkts):
        print('Could not find packet file {}'.format(args.pkts))
        sys.exit()

    # also check that in 0-32
    if args.start > args.end:
        print('Unexpected sentinel search start ({}) and ({}) values'.format(args.start, args.end))
        sys.exit()

    if args.border not in [2, 4, 8, 16, 32, 64, 128, 256, 512, 1024]:
        print('Number of border routers should be power of two and 2 <= N <= 1024: {}'.format(args.border))
        sys.exit()

    if args.traffic == 1:
        use_persistent = True
    else:
        use_persistent = False

    if args.magnifier == 1:
        make_sim_magnifier(args.pkts, args.outfile, args.frequency, args.duration,
                           args.pps, args.start, args.end, args.iteration,
                           args.border, use_persistent, args.amount)
    else:
        make_sim_everflow(args.pkts, args.outfile, args.frequency, args.duration,
                          args.pps, args.start, args.end, args.iteration,
                          args.border, use_persistent, args.amount)
