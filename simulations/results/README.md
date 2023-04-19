# Simulation results

The runner script will write results into this folder.

## Generate plot data

Use `python3 prepare_plot_data.py` to extract interesting plot points from
specific simulation runs. Add the results you would like to consider at the
beginning of the file in the list `result_folders`. There you can also specify
which default values to use for load, number of border routers and frequency. If
the specified input files do not contain simulation results for some of the
expected plot output values, a line with `-1` is written into the output file.

Also have a look at the `paper_plots` folder in the repository which contains
results used in the paper as well as Latex files to generate paper plots.
