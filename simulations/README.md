# Simulations

This folder contains the code and scripts to perform various Magnifier
simulations as well as comparison simulations with a partial Everflow
implementation (have a look at the paper for additional details). All the
following instructions assume that we have the necessary Python packages
installed as described in the main README.

## Prepare input data

Please follow the steps described in the **input_data** folder. You only need to
perform these steps once.

## (optional) Run unittests

We provide a few unittests which should all pass successfully. To run them,
please use:

`python3 sim_unittests.py`

## Run a single simulation

You can use the file `simulation.py` to run individual simulations. Use `python3
simulation.py -h` for a detailed list of input parameters. Following two example
run commands to produce partial simulation runs:
- Magnifier: `python3 simulation.py -P 50000 -i 10 -d 30 -P 166 -p ../input_data/simulation_input.csv -o test_run_magnifier.csv -m 1`
- Everflow: `python3 simulation.py -P 50000 -i 10 -d 30 -P 166 -p ../input_data/simulation_input.csv -o test_run_everflow.csv -m 0`

## Run all simulations

We also provide a script which orchestrates multiple simulation runs
automatically. Adapt the parameters at the beginning of `runner.py` if needed.
Afterwards execute:

`python3 runner.py`

## Generate plot results

Follow the instructions in the results folder to prepare the simulation results
from the runner for plotting.
