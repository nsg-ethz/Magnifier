# runs given comand on device
# key-based ssh authentication assumed
#
# usage: ./run_single_cmd.sh <cmd>

ssh -i ~/.ssh/cisco admin@10.70.0.1 "python3 run_cmd.py --cmd=$1"
