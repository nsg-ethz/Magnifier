from datetime import datetime
from ip_conversion import ipv4_to_str, ipv4_to_int


def preprocess(infile, outfile):
    """ Preprocesses a given input packet csv file to only contain the relevant data
    We will generate an output csv file which contains the following columns:
    - float timestamp
    - src IP as int
    - source IP /24 prefix as string
    - border router if random (worst case), for 4, 8, 16, 32, 64 routers
    - border router if consistent (best case), for 4, 8, 16, 32, 64 routers
    - flag bit (1 if at least one everflow bit is set)

    We skip input packets which are incomplete

    args:
        infile (str): input file name
        outfile (str): output file name
    """

    print('starting to preprocess {} at {}'.format(infile, datetime.now()))

    border_dict_4 = dict()
    border_dict_8 = dict()
    border_dict_16 = dict()
    border_dict_32 = dict()
    border_dict_64 = dict()
    ip_slice_4 = int(2**32 / 4)
    ip_slice_8 = int(2**32 / 8)
    ip_slice_16 = int(2**32 / 16)
    ip_slice_32 = int(2**32 / 32)
    ip_slice_64 = int(2**32 / 64)

    i = 0

    with open(infile, 'r') as data_in, open(outfile, 'w') as data_out:
        for line in data_in:
            ts, src_ip, dst_ip, ip_id, _, _, syn, fin, rst = line.strip().split(',')[:9]
            if not dst_ip:
                continue

            src_ip_int = ipv4_to_int(src_ip)
            temp = (src_ip_int >> 8) << 8
            prefix_24 = ipv4_to_str(temp)+'/24'

            dst_ip_int = ipv4_to_int(dst_ip)
            router_4 = int(dst_ip_int / ip_slice_4) + 1
            router_8 = int(dst_ip_int / ip_slice_8) + 1
            router_16 = int(dst_ip_int / ip_slice_16) + 1
            router_32 = int(dst_ip_int / ip_slice_32) + 1
            router_64 = int(dst_ip_int / ip_slice_64) + 1

            if prefix_24 not in border_dict_4:
                border_dict_4[prefix_24] = router_4
                border_dict_8[prefix_24] = router_8
                border_dict_16[prefix_24] = router_16
                border_dict_32[prefix_24] = router_32
                border_dict_64[prefix_24] = router_64

            if syn == '1' or fin == '1' or rst == '1':
                flags = '1'
            else:
                flags = '0'

            data_out.write('{},{},{},{},{},{},{},{},{},{},{},{},{},{}\n'.format(
                ts,
                src_ip_int,
                prefix_24,
                router_4,
                router_8,
                router_16,
                router_32,
                router_64,
                border_dict_4[prefix_24],
                border_dict_8[prefix_24],
                border_dict_16[prefix_24],
                border_dict_32[prefix_24],
                border_dict_64[prefix_24],
                flags
            ))

            i += 1
            if i % 100000000 == 0:
                print('processed {} pkts at {}'.format(i, datetime.now()))


if __name__ == "__main__":
    infile = 'simulation_input_temp.csv'
    outfile = 'simulation_input.csv'

    preprocess(infile, outfile)
