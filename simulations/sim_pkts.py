""" Simulation functions related to packets
"""

from sim_util import get_router_n
from common.ip_conversion import ipv4_to_str, ipv4_to_int
import random


def prepare_permutations(percentage, prefix_file, n_routers):
    """ Prepares prefix permutations

    percentage (int):
        percentage of changes between 0 and 100
    prefix_file (str):
        file which contains all /24 source prefixes in the CAIDA trace
    n_routers (int):
        number of border routers to consider

    returns: {prefix: router}
        dict which maps prefix to router
    """

    mapping = dict()
    slice_size = 2**32 / n_routers

    with open(prefix_file, 'r') as data_in:
        for line in data_in:
            prefix = line.strip()
            a, _, _, _ = prefix.split('.')

            # routers are from 0 ... n-1
            router = int(int(a) / slice_size + 1)
            mapping[prefix] = router

    amount = len(mapping)
    to_change = int(amount / 100 * percentage)

    # get random prefixes to change
    selected_prefixes = random.sample(list(mapping.items()), to_change)

    n = 0
    for prefix, router in selected_prefixes:
        # change router for selected prefixes
        # we add in order 0...(n_routers-1) to it
        mapping[prefix] = int((router + n % (n_routers - 1)) % n_routers + 1)
        n += 1

    return mapping


def get_preprocessed_pkts_mapping(data_in, start, end, replay_real_speed, n_border, mapping, time_persistent=False):
    """ More efficient way to only get required packets for current iteration
    This function supports both, PPS and real time speed

    data_in (open file):
        input file open at end of last iteration
    start (int):
        start pkt number or time
    end (int):
        end pkt number or time
    replay_real_speed (bool):
        to distinguish between PPS and real time speed
    n_border (int):
        number of border routers
    mapping (dict):
        maps /24 prefix to border router
    time_persistent (bool):
        set to true to use persistent source 24 prefix to ingress router mapping (default false)

    returns: (pkts, timestamps, flags, file_ptr, border_pkts, border_flags)
        pkts:
            list of (src IP as int, corresponding /24 prefix, ingress router)
        timestamps:
            list of pkt timestamps
        flags:
            list of booleans if at least one everflow TCP flag is set
        file_ptr:
            open file at end of current iteration
        border_pkts:
            packets separated by border router
        border_flags:
            flags separated by border router
    """

    # initialization outputs
    pkts = list()
    timestamps = list()
    flags = list()

    border_pkts = [[] for i in range(n_border)]
    border_flags = [[] for i in range(n_border)]

    slice_duration = end - start

    i = 0

    for line in data_in:
        ts, src_ip_int, prefix_24, rnd_4, rnd_8, rnd_16, rnd_32, rnd_64, per_4, per_8, per_16, per_32, per_64, flag = line.strip().split(',')

        if i == 0:
            start_ts = int(float(ts))

        i += 1

        timestamps.append(float(ts))

        # router assignment based on permuted mapping
        router = mapping[prefix_24]

        if flag == '1':
            flags.append(True)
            border_flags[router - 1].append(True)
        else:
            flags.append(False)
            border_flags[router - 1].append(False)

        pkts.append((int(src_ip_int), prefix_24, router))
        border_pkts[router - 1].append((int(src_ip_int), prefix_24, router))

        if not replay_real_speed:
            if i == slice_duration:
                break
        else:
            if int(float(ts)) - start_ts >= slice_duration:
                break

    return (pkts, timestamps, flags, data_in, border_pkts, border_flags)


def get_preprocessed_pkts(data_in, start, end, replay_real_speed, n_border, time_persistent=False):
    """ More efficient way to only get required packets for current iteration
    This function supports both, PPS and real time speed

    data_in (open file):
        input file open at end of last iteration
    start (int):
        start pkt number or time
    end (int):
        end pkt number or time
    replay_real_speed (bool):
        to distinguish between PPS and real time speed
    n_border (int):
        number of border routers
    time_persistent (bool):
        set to true to use persistent source 24 prefix to ingress router mapping (default false)

    returns: (pkts, timestamps, flags, file_ptr, border_pkts, border_flags)
        pkts:
            list of (src IP as int, corresponding /24 prefix, ingress router)
        timestamps:
            list of pkt timestamps
        flags:
            list of booleans if at least one everflow TCP flag is set
        file_ptr:
            open file at end of current iteration
        border_pkts:
            packets separated by border router
        border_flags:
            flags separated by border router
    """

    # initialization outputs
    pkts = list()
    timestamps = list()
    flags = list()

    border_pkts = [[] for i in range(n_border)]
    border_flags = [[] for i in range(n_border)]

    slice_duration = end - start

    i = 0

    for line in data_in:
        ts, src_ip_int, prefix_24, rnd_4, rnd_8, rnd_16, rnd_32, rnd_64, per_4, per_8, per_16, per_32, per_64, flag = line.strip().split(',')

        if i == 0:
            start_ts = int(float(ts))

        i += 1

        timestamps.append(float(ts))

        # make nicer
        if n_border == 4:
            if time_persistent:
                router = int(per_4)
            else:
                router = int(rnd_4)
        elif n_border == 8:
            if time_persistent:
                router = int(per_8)
            else:
                router = int(rnd_8)
        elif n_border == 16:
            if time_persistent:
                router = int(per_16)
            else:
                router = int(rnd_16)
        elif n_border == 32:
            if time_persistent:
                router = int(per_32)
            else:
                router = int(rnd_32)
        elif n_border == 64:
            if time_persistent:
                router = int(per_64)
            else:
                router = int(rnd_64)

        if flag == '1':
            flags.append(True)
            border_flags[router - 1].append(True)
        else:
            flags.append(False)
            border_flags[router - 1].append(False)

        pkts.append((int(src_ip_int), prefix_24, router))
        border_pkts[router - 1].append((int(src_ip_int), prefix_24, router))

        if not replay_real_speed:
            if i == slice_duration:
                break
        else:
            if int(float(ts)) - start_ts >= slice_duration:
                break

    return (pkts, timestamps, flags, data_in, border_pkts, border_flags)


def get_pkts_efficient(data_in, start, end, ip_slice, replay_real_speed, n_border, time_persistent=False, border_dict=None):
    """ More efficient way to only get required packets for current iteration
    This function supports both, PPS and real time speed

    data_in (open file):
        input file open at end of last iteration
    start (int):
        start pkt number or time
    end (int):
        end pkt number or time
    ip_slice (int):
        IP slice belonging to one ingress router
    replay_real_speed (bool):
        to distinguish between PPS and real time speed
    n_border (int):
        number of border routers
    time_persistent (bool):
        set to true to get persistent source 24 prefix to ingress router mapping (default false)
    border_dict (dict):
        used to save currently used mapping (if time_persistent is true, otherwise None)

    returns: (pkts, timestamps, flags, file_ptr, border_pkts, border_flags)
        pkts:
            list of (src IP as int, corresponding /24 prefix, ingress router)
        timestamps:
            list of pkt timestamps
        flags:
            list of booleans if at least one Everflow TCP flag is set
        file_ptr:
            open file at end of current iteration
        border_pkts:
            packets separated by border router
        border_flags:
            flags separated by border router
    """

    # initialization outputs
    pkts = list()
    timestamps = list()
    flags = list()

    border_pkts = [[] for i in range(n_border)]
    border_flags = [[] for i in range(n_border)]

    slice_duration = end - start

    i = 0

    for line in data_in:
        ts, src_ip, dst_ip, ip_id, _, _, syn, fin, rst = line.strip().split(',')[:9]
        if not dst_ip:
            continue

        if i == 0:
            start_ts = int(float(ts))

        i += 1

        timestamps.append(float(ts))
        src_ip_int = ipv4_to_int(src_ip)
        temp = (src_ip_int >> 8) << 8
        prefix_24 = ipv4_to_str(temp)+'/24'

        if time_persistent:
            if prefix_24 not in border_dict:
                # if we do not yet know the border router we use the existing
                # random assignment based on the dst IP
                router = int(ipv4_to_int(dst_ip) / ip_slice) + 1
                border_dict[prefix_24] = router
            else:
                router = border_dict[prefix_24]
        else:
            router = int(ipv4_to_int(dst_ip) / ip_slice) + 1

        if syn == '1' or fin == '1' or rst == '1':
            flags.append(True)
            border_flags[router - 1].append(True)
        else:
            flags.append(False)
            border_flags[router - 1].append(False)

        pkts.append((src_ip_int, prefix_24, router))
        border_pkts[router - 1].append((src_ip_int, prefix_24, router))

        if not replay_real_speed:
            if i == slice_duration:
                break
        else:
            if int(float(ts)) - start_ts >= slice_duration:
                break

    return (pkts, timestamps, flags, data_in, border_pkts, border_flags)


# no longer used
def get_pkts(filename, iteration, duration, pps, boundaries):
    """ Returns packets and timestamps for simulation

    filename (str): 
        input csv file
    iteration (int): 
        number of iterations
    duration (int): 
        how long one iteration takes (in seconds)
    pps (int): 
        replayed packets per second
    boundaries (list): 
        IP space boundaries to find border router

    returns: (pkts, timestamps, flags)
        pkts: 
            list of (src IP as int, corresponding /24 prefix, ingress router)
        timestamps: 
            list of pkt timestamps
        flags: 
            list of booleans if at least one everflow TCP flag is set
    """

    # initialization outputs
    pkts = list()
    timestamps = list()
    flags = list()

    # total number of packets needed
    end = (iteration) * duration * pps

    with open(filename, 'r') as data_in:
        # using dedicated counter to make sure we always get expected
        # amount of packets, even if we skip some due to missing data
        # in the underlying CAIDA trace.
        i = 0

        for line in data_in:
            if i == end:
                break

            ts, src_ip, dst_ip, ip_id, _, _, syn, fin, rst = line.strip().split(',')[:9]
            if not dst_ip:
                continue

            i += 1

            if syn == '1' or fin == '1' or rst == '1':
                flags.append(True)
            else:
                flags.append(False)

            timestamps.append(float(ts))
            router = get_router_n(ipv4_to_int(dst_ip), boundaries)
            src_ip_int = ipv4_to_int(src_ip)
            temp = (src_ip_int >> 8) << 8
            prefix_24 = ipv4_to_str(temp)+'/24'

            pkts.append((src_ip_int, prefix_24, router))

    return (pkts, timestamps, flags)


# no longer used
def get_pkts_time_slice(filename, iteration, duration, boundaries):
    """ Returns packets and timestamps for simulation based on real time

    filename (str): 
        input csv file
    iteration (int): 
        number of iterations
    duration (int): 
        how long one iteration takes (in seconds)
    boundaries (list): 
        IP space boundaries to find border router

    returns: (pkts, times, timestamps, flags)
        pkts: 
            list of (src IP as int, corresponding /24 prefix, ingress router)
        times: 
            list of packet counters which separate different iterations
        timestamps: 
            list of pkt timestamps
        flags: 
            list of booleans if at least one everflow TCP flag is set
    """

    # simulation end time
    end = (iteration) * duration

    current_time = 0
    pkts = list()
    times = list()
    timestamps = list()
    flags = list()

    # counter for actually considered packets
    j = 0
    with open(filename, 'r') as data_in:
        for i, line in enumerate(data_in):
            ts, src_ip, dst_ip, ip_id, _, _, syn, fin, rst = line.strip().split(',')[:9]
            if i == 0:
                start_ts = int(float(ts))
                times.append(j)
                current_time = int(float(ts))

            if not dst_ip:
                continue

            j += 1

            if syn == '1' or fin == '1' or rst == '1':
                flags.append(True)
            else:
                flags.append(False)

            if int(float(ts)) >= current_time + duration:
                times.append(j)
                current_time = int(float(ts))

            timestamps.append(float(ts))
            router = get_router_n(ipv4_to_int(dst_ip), boundaries)
            src_ip_int = ipv4_to_int(src_ip)
            temp = (src_ip_int >> 8) << 8
            prefix_24 = ipv4_to_str(temp)+'/24'

            pkts.append((src_ip_int, prefix_24, router))

            if int(float(ts)) - start_ts >= end:
                times.append(j)
                break

    return (pkts, times, timestamps, flags)


def get_sampled_packets(pkts, frequency):
    """ Get sampled packets

    pkts (list): list of packets
    frequency (int): n for sampling frequency 1/n

    returns: list with sampled packets
    """

    start = random.randrange(0, frequency)

    sampled_pkts = list()
    while start < len(pkts):
        sampled_pkts.append(pkts[start])
        start += frequency

    return sampled_pkts


def get_sampled_packets_per_router(border_pkts, border_flags, check_flag, frequency, to_sample):
    """ Get sampled packets for each border router individually

    border_pkts (list of lists): packets separated by border routers
    border_flags (list of lists): flags separated by border routers
    check_flag (bool): consider flags, yes or no
    frequency (int): n for sampling frequency 1/n
    to_sample (list of ints): sampling progress for each border router

    returns: (pkts, progress)
        pkts: list of sampled packets
            -> note that the returned pkts are no longer in chronologically order
            but that should not make a difference (e.g., for sentinel computation)
        progress: current sampling progress for next iteration
    """

    sampled_pkts = list()
    for i, location in enumerate(to_sample):
        # get all sampled packets for the current iteration
        while location < len(border_pkts[i]):
            # only add sample if we do not care about flags or it does not have one
            if not check_flag or not border_flags[i][location]:
                sampled_pkts.append(border_pkts[i][location])
            location += frequency

        # take over progress to the next iteration
        to_sample[i] = location - len(border_pkts[i])

    return (sampled_pkts, to_sample)


def get_sampled_packets_everflow(pkts, flags, border_pkts, border_flags, frequency, to_sample):
    """ Get sampled packets for everflow (flags + random)

    pkts (list): list of all packets
    flags (list): list of booleans if packet has flags set 
    border_pkts (list of lists): packets separated by border routers
    border_flags (list of lists): flags separated by border routers
    frequency (int): n for sampling frequency 1/n
    to_sample (list of ints): sampling progress for each border router

    returns: (pkts, progress, n_flag, n_random)
        pkts: list of sampled packets
            -> note that the returned pkts are no longer in chronologically order
            but that should not make a difference (e.g., for sentinel computation)
        progress: current sampling progress for next iteration
        n_flag: number of sampled packets due to flags
        n_random: number of sampled packets due to random sampling
            -> n_random does not count random samples with flags
    """

    sampled_pkts = list()

    # add all packets with flags
    for i, flag in enumerate(flags):
        if flag:
            sampled_pkts.append(pkts[i])

    # add randomly sampled packets which have no flags
    sampled_pkts_random, to_sample = get_sampled_packets_per_router(
            border_pkts,
            border_flags,
            True,
            frequency,
            to_sample
        )

    return (sampled_pkts+sampled_pkts_random, to_sample, len(sampled_pkts), len(sampled_pkts_random))
