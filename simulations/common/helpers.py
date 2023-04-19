import sys
import logging


def setup_logging(loglevel="DEBUG", logfile='temp_runner.log'):
    """Setup basic logging (to stdout and log file)

    Args:
      loglevel (int): minimum loglevel for emitting messages
      logfile (str): path to logfile
    """
    logformat = "[%(asctime)s] %(levelname)s:%(name)s:%(message)s"
    logging.basicConfig(level=loglevel,
                        handlers=[logging.FileHandler(logfile),
                                  logging.StreamHandler(stream=sys.stdout)],
                        format=logformat, datefmt="%Y-%m-%d %H:%M:%S")
