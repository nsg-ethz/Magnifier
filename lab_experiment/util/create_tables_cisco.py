""" Utility functions to get pandas table based on the mirrored
    and sampled data from the Cisco Nexus switches.
"""

import pandas as pd
import numpy as np
import logging
from ip_conversion import ipv4_to_int

logging.getLogger("get.table_c").setLevel(logging.DEBUG)

FORMAT = "[GET_TABLE_C:%(lineno)3s - %(funcName)12s()] %(message)s"
logging.basicConfig(format=FORMAT)
LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)


MAC_TO_ROUTER = {'00:ea:bd:56:a9:77': 1}
MAC_TO_DST = {'00:ea:bd:56:a9:77': 'in'}
IP_TO_ROUTER = {'436209664': 1, '436211712': 2, '436233216': 3, '436234240': 4}
ID_TO_DST = {'436233216': 'in', '436211200': 'out'}


def get_router(ip):
    # 0
    # 1073741824
    # 2147483648
    # 3221225472
    if 0 <= ip < 1073741824:
        return 1
    if 1073741824 <= ip < 2147483648:
        return 2
    if 2147483648 <= ip < 3221225472:
        return 3
    if 3221225472 <= ip:
        return 4


def get_mirrored_table(filename, start_line):
    """ Function to get pandas table from mirrored data

    Args:
        filename (string): file to read from
        start_line (int): line to start in collected pcap file

    Returns:
        (in table, out table, end_line): as pandas table with corresponding packets
    """

    # example csv entry for mirrored traffic:
    # 1629972461.823216000,00:ea:bd:56:a9:77,90:e2:ba:b6:1c:f0,90:e2:ba:b6:1c:f1,00:ea:bd:56:a9:77,47,6,10.70.0.1,197.16.34.18,10.70.0.2,10.90.0.1,443,52523,,
    # 1630650206.713038056, f8:0f:6f:96:1c:bf, 00:ea:bd:56:a9:77, 90:e2:ba:b6:1c:f2, f8:0f:6f:96:1c:bf, 47, 6, 10.80.0.1, 197.202.25.96, 10.80.0.2, 202.28.87.189

    ii = 0
    counters = [0, 0, 0, 0]

    with open(filename, 'r') as data_in:
        in_table = list()
        out_table = list()

        for ii, line in enumerate(data_in):
            if ii <= start_line:
                continue

            cells = line.strip().split(',')
            if len(cells) != 11:
                continue

            # make sure we have expected timestamp format
            ts = int(float(cells[0])*1000)

            if cells[8] == "" or cells[10] == "":
                continue

            # as we sometimes read in the file when the last line is not completely written (incomplete dst IP)
            try:
                src_ip = ipv4_to_int(cells[8])
                dst_ip = ipv4_to_int(cells[10])
            except OSError:
                print('invalid IPs in', cells[8], cells[10])
                continue

            router = get_router(dst_ip)
            direction = 'in'

            counters[router-1] += 1

            # one packet per line so we always report 1
            if direction == 'in':
                in_table.append((router, src_ip, dst_ip, ts, 1))
            else:
                out_table.append((router, src_ip, dst_ip, ts, 1))

    column_type = [('router_ip', 'uint32'), ('src_ip', 'uint32'),
                   ('dst_ip', 'uint32'), ('ts_end', 'uint64'),
                   ('pkts', 'uint32')]

    in_arr = np.array(in_table, dtype=column_type)
    in_arr_final = pd.DataFrame.from_records(in_arr)

    out_arr = np.array(out_table, dtype=column_type)
    out_arr_final = pd.DataFrame.from_records(out_arr)

    return (in_arr_final, out_arr_final, ii, counters)


def get_sampled_table(filename):
    """ Function to get pandas table from sampled data

    Args:
        filename (string): file to read from

    Returns:
        (in table, out table): as pandas table with corresponding packets
    """

    # example csv entry for sampled sflow traffic:
    # Date first seen (raw), Date last seen (raw), Date flow received (raw), Duration, Proto, Src IP Addr, Dst IP Addr, Src Pt, Dst Pt, In Pkt, Out Pkt, In Byte, Out Byte, Flows, Exp ID, Router IP, Input, Output
    #    1630411579.810,1630411579.810,0.000,    0.000,TCP  ,   44.85.129.200,       10.90.0.2,   443, 36264,    4096,       0,  270336,       0,    1,     1,         0.0.0.0,436233216,436211200

    with open(filename, 'r') as data_in:
        in_table = list()
        out_table = list()

        for line in data_in:
            # also remove spaces around entries
            cells = [x.strip() for x in line.strip().split(',')]

            if len(cells) != 18:
                continue

            if cells[17] not in IP_TO_ROUTER:
                continue

            router = IP_TO_ROUTER[cells[17]]
            direction = 'in'

            # make sure we have expected timestamp format
            ts = int(float(cells[0])*1000)

            src_ip = ipv4_to_int(cells[5])
            dst_ip = ipv4_to_int(cells[6])
            pkts = int(cells[9])

            if direction == 'in':
                in_table.append((router, src_ip, dst_ip, ts, pkts))
            else:
                out_table.append((router, src_ip, dst_ip, ts, pkts))

    column_type = [('router_ip', 'uint32'), ('src_ip', 'uint32'),
                   ('dst_ip', 'uint32'), ('ts_end', 'uint64'),
                   ('pkts', 'uint32')]

    in_arr = np.array(in_table, dtype=column_type)
    in_arr_final = pd.DataFrame.from_records(in_arr)

    out_arr = np.array(out_table, dtype=column_type)
    out_arr_final = pd.DataFrame.from_records(out_arr)

    return (in_arr_final, out_arr_final)


if __name__ == '__main__':
    get_mirrored_table('../mirrored/dummy.csv', 0)
