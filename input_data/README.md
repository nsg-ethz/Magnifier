# Input data

For our simulations and lab experiments we used data from [CAIDA
traces](https://www.caida.org/catalog/datasets/passive_dataset/). In the paper
we used an entire one-hour long trace from 2018 (2018.03.15, A direction).
Unfortunately, we cannot provide the corresponding CAIDA data in this GitHub
repository. Please download the corresponding pcap files from the CAIDA website
directly. Additionally, any other CAIDA trace (or potentially also other packet
traces) should work as input data. The trace used in the paper produced the
following [capinfos](https://www.wireshark.org/docs/man-pages/capinfos.html)
output:

```
# capinfos           <caida_data_used_in_the_paper>
File name:           <filename>
File type:           Wireshark/tcpdump/... - pcap
File encapsulation:  Ethernet
File timestamp precision:  microseconds (6)
Packet size limit:   file hdr: 65535 bytes
Number of packets:   1572 M
File size:           116 GB
Data size:           91 GB
Capture duration:    3719.474398 seconds
First packet time:   2018-03-15 13:59:10.461923
Last packet time:    2018-03-15 15:01:09.936321
Data byte rate:      24 MBps
Data bit rate:       196 Mbps
Average packet size: 57.97 bytes
Average packet rate: 422 kpackets/s
SHA256:              180f4ae6958d7feb71cd71c0d7d8b257f0a7eb3ecc9674544d49eabf7afc46e9
RIPEMD160:           37006c76b55e5fc73ba4a3e0290a38a44c1a535b
SHA1:                945d5176f2fb83e1039227017e2e394788d30ff3
Strict time order:   True
Number of interfaces in file: 1
Interface #0 info:
                     Encapsulation = Ethernet (1 - ether)
                     Capture length = 65535
                     Time precision = microseconds (6)
                     Time ticks per second = 1000000
                     Number of stat entries = 0
                     Number of packets = 1572000000
```

For the simulation and hardware experiments we had to modify the CAIDA trace
slightly as described in the following subsections. To follow these steps you might need to install additional tools, e.g., using commands such as:
```
sudo apt install wireshark-common 
sudo apt install tcpreplay
sudo apt install tshark
```

## Preparing a CAIDA trace for hardware experiments

In order to use one of the CAIDA traces in our hardware experiments we performed
the following steps. Note that most of them are necessary as otherwise the used
hardware might not properly handle the replayed CAIDA packets.

1. (optional) extract a certain amount of packets from the full CAIDA trace. For
   example, the following command extracts the first 1000 packets:\
`editcap -r <input_caida_trace.gz> <output_trace.pcap> 0-1000`

1. (required) add Ethernet headers to the trace matching the experiment setup.
   You have to adapt the source and destination MAC addresses according to your
   setup:\
`tcprewrite --dlt=enet --enet-smac=<MAC_of_replay_server> --enet-dmac=<MAC_of_switch_router> --infile=<input_trace.pcap> --outfile=<output_trace.pcap>`

1. (required) make sure that the payload length in the packets match with what
   is physically available in the trace (as CAIDA removes the payload). The best
   option would be to pad the truncated CAIDA packets to match the payload
   length using the following command:\
`tcprewrite --fixlen=pad --infile=<input_trace.pcap> --outfile=<output_trace.pcap>`\
   However, this command did not work correctly in our setup. As a workaround,
   we can also truncate all packets to a length of zero using the following
   command:\
`tcprewrite --fixlen=trunc --infile=<input_trace.pcap> --outfile=<output_trace.pcap>`

1. (required) in our lab setup we only had two devices available. We had to
   squeeze the sampling and mirroring operations on these two devices while
   simulating four different network devices (for a slightly more realistic
   evaluation). We therefore have to mark certain packets in the TOS field. To
   make sure that we not get any false flags, we remove all existing TOS values
   with the following command:\
`tcprewrite --tos=0 --infile=<input_trace.pcap> --outfile=<output_trace.pcap>`

1. (required) due to CAIDA's anonymization process, some destination IPs are
   translated into the reserved multicast address space which resulted in
   unexpected behavior on the switches (at least in our setup). Packets which
   have IPs in this prefix space are moved to another one using the following
   command:\
`tcprewrite --dstipmap=224.0.0.0/4:208.0.0.0/4 --infile=<input_trace.pcap> --outfile=<output_trace.pcap>`

## Preparing a CAIDA trace for simulations

If we already have a pcap file created following the steps above, we can use
this one for the simulations without any further changes. However, if we want to
create a trace for the simulations only, we should be able to use the CAIDA
trace directly.

Although it would be possible to directly use the CAIDA trace as input to the
simulations, continuously extracting and processing the packets from the pcap
trace adds significant delays. We therefore preprocessed the simulation input
and only stored the relevant packet information in a csv file.

We perform two pre-processing steps. First, we extract the relevant packet
headers from the trace using the following command:

```
tshark -r <input_trace.pcap> -E separator=, -T fields -e frame.time_epoch -e ip.src -e ip.dst -e ip.id -e tcp.srcport -e tcp.dstport -e tcp.flags.syn -e tcp.flags.fin -e tcp.flags.reset -e udp.srcport -e udp.dstport > simulation_input_temp.csv
```

Second, we run the following Python script to create the final simulation input
file which contains pre-computed simulation inputs (for Magnifier and comparison
simulations with Everflow). You can change the name of the generated file
directly in the script. By default it will be called: `simulation_input.csv`.

`python3 preprocess_pkt_csv.py`

As a final step, we also generate a file which contains prefix-related
information extracted from the preprocessed simulation input. This file is
needed to run certain simulations.

`python3 analyze_prefix_space.py`
