"""Runner script for Magnifier and Everflow simulations
"""

from common.helpers import setup_logging
import sys
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

import logging
log = logging.getLogger(__name__)

# Change if you use a different pcap file
N_PACKETS_TOTAL = 1500000000

# Simulation parameters
n_border_routers = [32, 4, 8, 16, 64]
load_factor = [4, 1, 2, 12]
sampling_frequencies = [256, 512, 2048, 4096]

samples_per_iteration = 1000
duration = 60
iterations = 60
default_sampling_rate = 1024
default_border_routers = 32
permutation_values = {0: -1, 1: -1, 2: 5, 3: 20}

pcap = '../input_data/simulation_input.csv'


def run_simulation(command):
    """ Starts a single simulation run

    Args:
        command (str): command string to use
    """

    log.info("Running simulation...")

    result = subprocess.run(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    stdout = result.stdout.decode()
    error = result.stderr.decode()
    log.info("Result run_evaluation (if none, all correct): {}".format(error))
    log.info("{}".format(stdout))


def parse_args(args):
    """Parse command line parameters

    Args:
      args ([str]): command line parameters as list of strings

    Returns:
      :obj:`argparse.Namespace`: command line parameters namespace
    """

    parser = argparse.ArgumentParser(
        description="Magnifier simulation runner")

    # Dummy argument
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
    parser.add_argument(
        '-m',
        '--magnifier',
        default=1,
        type=int,
        help='use magnifier (1) or everflow (0)')
    parser.add_argument(
        '-t',
        '--traffic',
        default=1,
        type=int,
        help='pkt to border mapping in the best (1, default) or worst (0) way')
    parser.add_argument(
        '-e', '--experiment',
        default=2,
        type=int,
        help='experiment type to run (1: old, 2: border/load, 3: frequency')

    return parser.parse_args(args)


def prepare_single_run(n_border_router, load, pps, sampling_rate, result_path, use_magnifier, use_persistent, now):
    """ Prepares a single simulation run

    Args:
        n_border_router (int): number of border routers
        load (int): load factor
        pps (int): PPS for simulation
        sampling_rate (int): sampling rate
        result_path (str): path to result directory
        use_magnifier (int): use magnifier (1) or not (0)
        use_persistent (int): (0) random, (1) static, (2) permutation 5%, (3) permutation 20%
        now (datetime): runner start time
    """

    out = "{} {} {}".format(n_border_router, load, pps)
    log.debug(out)

    # approximate corresponding simulation time/iterations
    n_seconds_simulation = int(N_PACKETS_TOTAL / pps)
    n_iterations_simulation = int(n_seconds_simulation/duration)

    out = "=> {} seconds => {} iterations".format(n_seconds_simulation, n_iterations_simulation)
    log.debug(out)

    # Output file name
    out_file = "b_{}_l_{}_d_{}_f_{}_m_{}_t_{}.csv".format(
        n_border_router,
        load,
        duration,
        sampling_rate,
        use_magnifier,
        use_persistent
    )

    # Launch the simulation
    in_simu_verbosity = ''
    command = "python3 simulation.py -P {} -i {} -d {} -b {} -p {} -o {} -f {} -m {} -t {} -a {} {}".format(
        pps,
        iterations,
        duration,
        n_border_router,
        pcap,
        str(result_path / out_file),
        sampling_rate,
        use_magnifier,
        use_persistent,
        permutation_values[use_persistent],
        in_simu_verbosity
    )

    log.info("| #routers     | {} |".format(n_border_router))
    log.info("| load factor  | {} |".format(load))
    log.info("| frequency    | {} |".format(sampling_rate))
    log.info("| magnifier    | {} |".format(use_magnifier))
    log.info("| distribution | {} |".format(use_persistent))

    simu_start = datetime.now()
    run_simulation(command)
    simu_end = datetime.now()
    log.info("Last simulation took: {}".format(simu_end - simu_start))
    log.info("Running since: {}".format(simu_end - now))
    log.info(" ")


def main(args):
    """Main entry point allowing external calls

    Args:
      args ([str]): command line parameter list
    """

    # Create the result directory
    now = datetime.now()
    result_dir = now.strftime("%Y-%m-%d_%H-%M-%S")
    result_path = Path('results', result_dir)
    Path.mkdir(result_path, parents=True)

    # Initialize logging
    args = parse_args(args)
    logfile = '{}/logger_output_experiment_{}_magnifier_{}_persistent_{}.log'.format(
        result_path,
        args.experiment,
        args.magnifier,
        args.traffic)
    setup_logging(args.loglevel, logfile)

    # old experiments, not currently used in paper
    if args.experiment == 1:
        for n_border_router in n_border_routers:
            for load in load_factor:
                # compute the required packet rate to get
                # a fixed number of sampled packets
                # per iteration
                pps = int(
                    samples_per_iteration / duration
                    * default_sampling_rate
                    * load
                )

                # all old experiments used f=1024 by default
                prepare_single_run(n_border_router,
                                   load,
                                   pps,
                                   default_sampling_rate,
                                   result_path,
                                   args.magnifier,
                                   args.traffic,
                                   now)

    # experiments focused on border and load values (f=1024)
    elif args.experiment == 2:
        for n_border_router in n_border_routers:
            for load in load_factor:
                # keeping same load names for easier comparison with existing scripts
                # speed of hardware experiments
                if load == 1:
                    pps = 45000

                # 0.5x real speed
                if load == 2:
                    pps = int(N_PACKETS_TOTAL / 60 / 60 / 2)

                # real speed
                if load == 4:
                    pps = int(N_PACKETS_TOTAL / 60 / 60)

                # 2x real speed
                # will not give 100 iterations (only around 60)
                if load == 12:
                    pps = int(N_PACKETS_TOTAL / 60 / 60 * 2)

                # all uses 1024 sampling frequency
                prepare_single_run(n_border_router,
                                   load,
                                   pps,
                                   default_sampling_rate,
                                   result_path,
                                   args.magnifier,
                                   args.traffic,
                                   now)

    # experiments focused on load and sampling frequency (b=32)
    elif args.experiment == 3:
        for frequency in sampling_frequencies:
            for load in load_factor:
                # keeping same load names for easier comparison with existing scripts
                # speed of hardware experiments
                if load == 1:
                    pps = 45000

                # 0.5x real speed
                if load == 2:
                    pps = int(N_PACKETS_TOTAL / 60 / 60 / 2)

                # real speed
                if load == 4:
                    pps = int(N_PACKETS_TOTAL / 60 / 60)

                # 2x real speed
                # will not give 100 iterations (only around 60)
                if load == 12:
                    pps = int(N_PACKETS_TOTAL / 60 / 60 * 2)

                # all uses 32 border routers
                prepare_single_run(default_border_routers,
                                   load,
                                   pps,
                                   frequency,
                                   result_path,
                                   args.magnifier,
                                   args.traffic,
                                   now)


def run():
    """Entry point for console_scripts
    """
    main(sys.argv[1:])


if __name__ == "__main__":
    run()
