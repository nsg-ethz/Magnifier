# enables mirroring for given prefixes
# key-based ssh authentication is assumed
#
# usage: ./provision_mirroring.sh <prefixes R1> <prefixes R2> <prefixes R3> <prefixes R4> <iteration (1, 2)> <switch (-1, 0, 1, 2)> <run time of rule deletion>
# use comma-separated lists for the prefixes or "-" if one router does not need any prefixes

ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 provision_single_device_full.py --p=$1 --dev=1 --iter=$5" &
ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 provision_single_device_full.py --p=$2 --dev=2 --iter=$5" &
ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 provision_single_device_full.py --p=$3 --dev=3 --iter=$5" &
ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 provision_single_device_full.py --p=$4 --dev=4 --iter=$5" &

wait

ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 start_all_mirroring_switch.py --switch=$6"
