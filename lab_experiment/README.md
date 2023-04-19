# Lab experiments

This folder contains code and scripts related to the main lab experiment
described in the paper. This README tries to describe the main steps to run the
experiment on another setup, however it might be quite difficult to make it work
under a different environment. The provided scripts still contain IPs and
interface names used in our lab setup.

## Configure the devices accordingly

As a first step, configure the routers or switches accordingly to enable
connectivity, sampling and mirroring features. The files `device_1.conf` and
`device_2.conf` show our configurations.

## Upload files to switches/routers

We run certain commands directly on the switch or router using e.g., [Cisco's
Python
API](https://www.cisco.com/c/en/us/td/docs/switches/datacenter/nexus3600/sw/93x/programmability/guide/b-cisco-nexus-3600-nx-os-programmability-guide-93x/m-3600-python-api-93x.pdf).
To provision the required files on the device and to execute the commands from
within Magnifier's code base, we first need key-based ssh access to the switch
or router. To do so, enable the corresponding feature, e.g., `feature ssh` and
then follow the instructions
[here](https://www.cisco.com/c/en/us/support/docs/voice/mds/200640-Ssh-into-NX-OS-Switches-using-key-based.pdf).

Afterwards, we need to copy the following three scripts to the devices:
- `provision_single_device_full.py`
- `run_cmd.py`
- `start_all_mirroring_switch.py`

To do so, enable the scp feature on the devices, e.g., `feature scp-server`, and
copy the files using normal `scp` commands.

## Start to collect sampled data

To collect sampled data (produced by sFlow) on a server connected to the
switches or routers we used `sfcapd` which is part of the [nfdump
tools](https://github.com/phaag/nfdump). Install it e.g., with `sudo apt install
nfdump-sflow`. Then run the following command to continuously collect sampled
data (note that you need to adapt the IP address to your setup):

`sfcapd -p 7000 -b 10.70.0.2 -l sflow -t 5 -x "mv sflow/%f sflow/nfcapd_moved.%u"`

The `-t` and `-x` options make sure that the newest sampled data is always
written to a file, as we experienced problems with caching otherwise.

## Start to collect mirrored data

To collect mirrored packets we use
[tshark](https://www.wireshark.org/docs/man-pages/tshark.html). Install it with
`sudo apt install tshark` if needed. Then run the following command to
continuously collect mirrored packets (note that you need to adapt the interface
name to your setup):

`sudo tshark -i enp133s0f0 -E separator=, -T fields -e frame.time_epoch -e eth.src -e eth.dst -e ip.proto -e ip.src -e ip.dst > mirrored/dummy.csv`

The options make sure that the relevant header information from each packet are
directly written to a csv file that Magnifier reads.

## Start Magnifier

To start Magnifier, simply execute the following Python program in this folder:

`python3 main.py`

## Replaying a pcap

Finally, we need to replay the CAIDA data. To do so, first modify a
corresponding CAIDA trace according to the instructions in the `input_data`
folder. We then use [tcpreplay](https://tcpreplay.appneta.com/) to replay the
trace. Install it with `sudo apt install tcpreplay` if needed. Then reply the
traffic using the following command (note that you need to adapt the interface
name to your setup):

`sudo tcpreplay -p 44550 -i enp131s0f0 <file_to_replay.pcap>`

The `-p` command limits the packets to a specific rate per second that we used
in our lab experiment.
