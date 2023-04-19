from os import walk

# number of border routers to use for load- and frequency-based results
B_TO_USE = 32

# load to use for border- and frequency-based results (real speed)
L_TO_USE = 4

# frequency to use for border- and load-based results
F_TO_USE = 1024

# switch between 30 and 60
DURATION = 60

FLOAT_VALUES = [
    'iteration_end_ts'
]

# simulation results to consider: ADD YOUR RESULT NAMES HERE, e.g. '2022-01-01_18-03-02'
result_folders = [
    
]


def read_data(filename):
    """ Reads in all data from a simulation csv results file

    Args:
      filename (str): file to read

    Returns:
      dict (metric: values)
        metric: specific result metric
        values: list with values for each iteration
    """

    data = dict()

    with open(filename, 'r') as data_in:
        for line in data_in:
            cells = line.strip().split(',')

            if cells[0] not in FLOAT_VALUES:
                data[cells[0]] = [int(x) for x in cells[1:]]
            else:
                data[cells[0]] = [float(x) for x in cells[1:]]

    return data


def get_prefix_space_average(correct, correct_not_unique, not_active):
    """ Returns the average prefix space covered by sentinels with mirroring

    Args:
        correct (list): prefix counts for all correct inferences
        correct_not_unique (list): prefix counts for correct inferences which are not unique
        not_active (list): prefix counts which are not active in ground truth data
                           if None, it is ignored (for absolute values in gt data)

    Returns:
        computed average value
    """

    temp = list()
    for i in range(len(correct)):
        if not_active:
            temp.append((correct[i] - correct_not_unique[i] + not_active[i]))
        else:
            temp.append((correct[i] - correct_not_unique[i]))

    return get_average(temp)


def get_unique_coverage_average(correct, correct_not_unique, total):
    """ Returns the average coverage values for correctly (unique) packets
        or /24 prefixes based on ground truth data

    Args:
        correct (list): packet/prefix counts for all correct inferences
        correct_not_unique (list): packet/prefix counts for correct inferences which are not unique
        total (list): all packets/prefixes in one iteration

    Returns:
        computed average value
    """

    temp = list()
    for i in range(len(correct)):
        temp.append((correct[i] - correct_not_unique[i]) / total[i])

    return get_average(temp)


def get_average(data_1, data_2=None):
    """ Returns average values over input data

    Args:
      data_1 (list): main data source
      data_2 (list): optional, if given, average over (data_1 / data_2) is returned

    Returns:
      computed average value
    """

    if not data_2:
        return sum(data_1) / len(data_1)
    else:
        return sum([x/y for x, y in zip(data_1, data_2)]) / len(data_1)


def prepare_plot_data():
    """ Extracts all simulation results and prepares specific plot input files
    """

    data = dict()

    # get all simulation results in specified folders
    for result in result_folders:
        for (dirpath, _, filenames) in walk(result):
            for file in filenames:
                if file.endswith('csv'):
                    data_name = file.split('.')[0]
                    data_got = read_data(dirpath+'/'+file)
                    if data_name in data:
                        print('results for {} are available twice in given files'.format(data_name))
                        if data_got == data[data_name]:
                            print('   both files contain the same values')
                        else:
                            print('   the read in values differ!!!')
                            for key, value in data_got.items():
                                if key not in data[data_name]:
                                    print('   {} does not exist in old data'.format(key))
                                    data[data_name][key] = data_got[key]
                                elif data[data_name][key] != data_got[key]:
                                    print(key)
                                    print('   old:', get_average(data[data_name][key]))
                                    print('   new:', get_average(data_got[key]))
                                    # for now we want the newer values
                                    data[data_name][key] = data_got[key]

                    # in case of different entries, we keep the old ones
                    else:
                        data[data_name] = data_got

    n_border_routers = [4, 8, 16, 32, 64]
    load_factor = [1, 2, 4, 12]
    frequencies = [256, 512, 1024, 2048, 4096]
    top_k = [100, 500, 1000, 5000]
    ordering = ['activity', 'size', 'full']

    # prepare suffix list
    suffixes = list()
    for order in ordering:
        if order != 'full':
            for top in top_k:
                suffixes.append('top_{}_{}'.format(top, order))
        else:
            suffixes.append('full')

    # calculate all possible output data of interest
    output_data = dict()
    for m in [0, 1]:
        for t in [0, 1, 2, 3]:
            for border in n_border_routers:
                for load in load_factor:
                    for frequency in frequencies:
                        name = 'b_{}_l_{}_d_{}_f_{}_m_{}_t_{}'.format(
                            border,
                            load,
                            DURATION,
                            frequency,
                            m,
                            t,
                        )

                        # skip if current name not in input files
                        if name not in data:
                            continue

                        # compute pkt coverage and mirrored traffic values
                        # ... sampling only
                        output_data['coverage_sampling_prefix_{}'.format(name)] = get_unique_coverage_average(
                            data[name]['full_prefix_correct_sampling'],
                            data[name]['full_prefix_covered_not_unique_sampling'],
                            data[name]['n_prefixes']
                        )

                        output_data['coverage_sampling_packet_{}'.format(name)] = get_unique_coverage_average(
                            data[name]['full_pkt_covered_correct_sampling'],
                            data[name]['full_pkt_covered_correct_not_unique_sampling'],
                            data[name]['n_total_packets']
                        )

                        # ... sentinels based on samples
                        output_data['coverage_sentinel_sampling_prefix_{}'.format(name)] = get_unique_coverage_average(
                            data[name]['full_prefix_correct_sentinel'],
                            data[name]['full_prefix_covered_not_unique_sentinel'],
                            data[name]['n_prefixes']
                        )

                        output_data['coverage_sentinel_sampling_packet_{}'.format(name)] = get_unique_coverage_average(
                            data[name]['full_pkt_covered_correct_sentinel'],
                            data[name]['full_pkt_covered_not_unique_sentinel'],
                            data[name]['n_total_packets']
                        )

                        # ... everflow only
                        # ... ... mirrored traffic
                        if m == 0:
                            output_data['mirrored_traffic_everflow_{}'.format(name)] = get_average(
                                data[name]['n_mirrored_packets'],
                                data[name]['n_total_packets'],
                            )

                        # ... magnifier only
                        if m == 1:
                            # ... ... total active prefix space (same for all suffixes)
                            output_data['active_prefix_space_{}'.format(name)] = get_average(
                                    data[name]['n_prefixes'],
                            )

                            # ... ... absolute value of covered prefix space with samples only
                            #         note that we also count not unique prefixes to have same value for worst and best
                            output_data['coverage_sampling_prefix_absolute_{}'.format(name)] = get_average(
                                    data[name]['full_prefix_correct_sampling']
                            )

                            for suffix in suffixes:
                                # we do not have the suffix in all files:
                                if suffix + '_n_sentinels_total_mirroring' not in data[name]:
                                    output_data['sentinels_total_mirroring_{}_{}'.format(suffix, name)] = -1
                                    output_data['sentinels_added_mirroring_{}_{}'.format(suffix, name)] = -1
                                    output_data['sentinels_removed_mirroring_{}_{}'.format(suffix, name)] = -1
                                    output_data['coverage_sentinel_mirroring_prefix_{}_{}'.format(suffix, name)] = -1
                                    output_data['coverage_sentinel_mirroring_packet_{}_{}'.format(suffix, name)] = -1
                                    output_data['mirrored_traffic_magnifier_{}_{}'.format(suffix, name)] = -1
                                    output_data['verified_prefix_space_{}_{}'.format(suffix, name)] = -1
                                    output_data['verified_prefix_space_in_trace_{}_{}'.format(suffix, name)] = -1

                                else:
                                    # ... ... total and added/removed sentinels
                                    output_data['sentinels_total_mirroring_{}_{}'.format(suffix, name)] = get_average(
                                        data[name][suffix + '_n_sentinels_total_mirroring'],
                                    )

                                    output_data['sentinels_added_mirroring_{}_{}'.format(suffix, name)] = get_average(
                                        data[name][suffix + '_n_sentinels_added_mirroring'],
                                    )

                                    output_data['sentinels_removed_mirroring_{}_{}'.format(suffix, name)] = get_average(
                                        data[name][suffix + '_n_sentinels_removed_mirroring'],
                                    )

                                    # ... ... coverage
                                    output_data['coverage_sentinel_mirroring_prefix_{}_{}'.format(suffix, name)] = get_unique_coverage_average(
                                        data[name][suffix + '_prefix_correct_mirroring'],
                                        data[name][suffix + '_prefix_covered_not_unique_mirroring'],
                                        data[name]['n_prefixes']
                                    )

                                    output_data['coverage_sentinel_mirroring_packet_{}_{}'.format(suffix, name)] = get_unique_coverage_average(
                                        data[name][suffix + '_pkt_covered_correct_mirroring'],
                                        data[name][suffix + '_pkt_covered_not_unique_mirroring'],
                                        data[name]['n_total_packets']
                                    )

                                    # ... ... mirroring
                                    output_data['mirrored_traffic_magnifier_{}_{}'.format(suffix, name)] = get_average(
                                        data[name][suffix + '_n_mirrored_packets_mirroring'],
                                        data[name]['n_total_packets'],
                                    )

                                    # ... ... total prefix space coverage
                                    output_data['verified_prefix_space_{}_{}'.format(suffix, name)] = get_prefix_space_average(
                                        data[name][suffix + '_prefix_correct_mirroring'],
                                        data[name][suffix + '_prefix_covered_not_unique_mirroring'],
                                        data[name][suffix + '_prefix_not_active_mirroring'],
                                    )

                                    # ... ... total prefix space coverage (in gt data only)
                                    output_data['verified_prefix_space_in_trace_{}_{}'.format(suffix, name)] = get_prefix_space_average(
                                        data[name][suffix + '_prefix_correct_mirroring'],
                                        data[name][suffix + '_prefix_covered_not_unique_mirroring'],
                                        None,
                                    )

    # prepare the csv header line
    csv_header = list()
    for m in ['everflow', 'magnifier']:
        for t in ['worst', 'best', 'per_5', 'per_20']:
            csv_header.append('coverage_sampling_prefix_{}_{}'.format(m, t))
            csv_header.append('coverage_sampling_packet_{}_{}'.format(m, t))
            csv_header.append('coverage_sentinel_sampling_prefix_{}_{}'.format(m, t))
            csv_header.append('coverage_sentinel_sampling_packet_{}_{}'.format(m, t))

            if m == 'everflow':
                csv_header.append('mirrored_traffic_{}_{}'.format(m, t))

            if m == 'magnifier':
                csv_header.append('active_prefix_space_{}_{}'.format(m, t))
                csv_header.append('coverage_sampling_prefix_absolute_{}_{}'.format(m, t))

                for suffix in suffixes:
                    csv_header.append('sentinels_total_mirroring_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('sentinels_added_mirroring_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('sentinels_removed_mirroring_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('coverage_sentinel_mirroring_prefix_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('coverage_sentinel_mirroring_packet_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('mirrored_traffic_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('verified_prefix_space_{}_{}_{}'.format(suffix, m, t))
                    csv_header.append('verified_prefix_space_in_trace_{}_{}_{}'.format(suffix, m, t))

    # prepare processed output csv files
    # ... focused on different load values
    with open('plot_data/traffic_load_results.csv', 'w') as data_out:
        # csv header line
        data_out.write('{}\n'.format(','.join(
            [
                'load',
                'x_pos',
            ] +
            csv_header
            )))

        for i, load in enumerate(load_factor):
            data_out.write('{},{}'.format(load, i+1))

            for m in [0, 1]:
                for t in [0, 1, 2, 3]:
                    name = 'b_{}_l_{}_d_{}_f_{}_m_{}_t_{}'.format(
                            B_TO_USE,
                            load,
                            DURATION,
                            F_TO_USE,
                            m,
                            t,
                        )

                    # we add a line of -1 if data is not available in specified input files
                    if name not in data:
                        if m == 0:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(5)])))
                        if m == 1:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(78)])))
                        continue

                    data_out.write(',{}'.format(output_data['coverage_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sampling_packet_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_packet_{}'.format(name)]))

                    if m == 0:
                        data_out.write(',{}'.format(output_data['mirrored_traffic_everflow_{}'.format(name)]))

                    if m == 1:
                        data_out.write(',{}'.format(output_data['active_prefix_space_{}'.format(name)]))
                        data_out.write(',{}'.format(output_data['coverage_sampling_prefix_absolute_{}'.format(name)]))

                        for suffix in suffixes:
                            data_out.write(',{}'.format(output_data['sentinels_total_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_added_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_removed_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_prefix_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_packet_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['mirrored_traffic_magnifier_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_in_trace_{}_{}'.format(suffix, name)]))

            data_out.write('\n')

    # ... focused on different border values
    with open('plot_data/border_routers_results.csv', 'w') as data_out:
        # csv header line
        data_out.write('{}\n'.format(','.join(
            [
                'border',
                'x_pos',
            ] +
            csv_header
            )))

        for i, border in enumerate(n_border_routers):
            data_out.write('{},{}'.format(border, i+1))

            for m in [0, 1]:
                for t in [0, 1, 2, 3]:
                    name = 'b_{}_l_{}_d_{}_f_{}_m_{}_t_{}'.format(
                            border,
                            L_TO_USE,
                            DURATION,
                            F_TO_USE,
                            m,
                            t,
                        )

                    # we add a line of -1 if data is not available in specified input files
                    if name not in data:
                        if m == 0:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(5)])))
                        if m == 1:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(78)])))
                        continue

                    data_out.write(',{}'.format(output_data['coverage_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sampling_packet_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_packet_{}'.format(name)]))

                    if m == 0:
                        data_out.write(',{}'.format(output_data['mirrored_traffic_everflow_{}'.format(name)]))

                    if m == 1:
                        data_out.write(',{}'.format(output_data['active_prefix_space_{}'.format(name)]))
                        data_out.write(',{}'.format(output_data['coverage_sampling_prefix_absolute_{}'.format(name)]))

                        for suffix in suffixes:
                            data_out.write(',{}'.format(output_data['sentinels_total_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_added_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_removed_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_prefix_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_packet_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['mirrored_traffic_magnifier_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_in_trace_{}_{}'.format(suffix, name)]))

            data_out.write('\n')

    # ... focused on different frequency values
    with open('plot_data/sampling_frequency_results.csv', 'w') as data_out:
        # csv header line
        data_out.write('{}\n'.format(','.join(
            [
                'frequency',
                'x_pos',
            ] +
            csv_header
            )))

        for i, frequency in enumerate(frequencies):
            data_out.write('{},{}'.format(frequency, i+1))

            for m in [0, 1]:
                for t in [0, 1, 2, 3]:
                    name = 'b_{}_l_{}_d_{}_f_{}_m_{}_t_{}'.format(
                            B_TO_USE,
                            L_TO_USE,
                            DURATION,
                            frequency,
                            m,
                            t,
                        )

                    # we add a line of -1 if data is not available in specified input files
                    if name not in data:
                        if m == 0:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(5)])))
                        if m == 1:
                            data_out.write(',{}'.format(','.join(['-1' for x in range(78)])))
                        continue

                    data_out.write(',{}'.format(output_data['coverage_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sampling_packet_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_prefix_{}'.format(name)]))
                    data_out.write(',{}'.format(output_data['coverage_sentinel_sampling_packet_{}'.format(name)]))

                    if m == 0:
                        data_out.write(',{}'.format(output_data['mirrored_traffic_everflow_{}'.format(name)]))

                    if m == 1:
                        data_out.write(',{}'.format(output_data['active_prefix_space_{}'.format(name)]))
                        data_out.write(',{}'.format(output_data['coverage_sampling_prefix_absolute_{}'.format(name)]))

                        for suffix in suffixes:
                            data_out.write(',{}'.format(output_data['sentinels_total_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_added_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['sentinels_removed_mirroring_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_prefix_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['coverage_sentinel_mirroring_packet_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['mirrored_traffic_magnifier_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_{}_{}'.format(suffix, name)]))
                            data_out.write(',{}'.format(output_data['verified_prefix_space_in_trace_{}_{}'.format(suffix, name)]))

            data_out.write('\n')


if __name__ == "__main__":
    prepare_plot_data()
