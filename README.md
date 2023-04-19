# Magnifier

This is the official repository for our Magnifier paper at NSDI 2023. You can find the paper [here](https://www.usenix.org/conference/nsdi23/presentation/buhler).

If you use part of the data or code in this repository, please cite our work:

```
@inproceedings {magnifier,
  author = {Tobias B{\"u}hler and Romain Jacob and Ingmar Poese and Laurent Vanbever},
  title = {{Enhancing Global Network Monitoring with Magnifier}},
  booktitle = {20th USENIX Symposium on Networked Systems Design and Implementation (NSDI 23)},
  year = {2023},
  address = {Boston, MA},
  url = {https://www.usenix.org/conference/nsdi23/presentation/buhler},
  publisher = {USENIX Association},
}
```

The **simulations** and **lab_experiment** folder contain corresponding scripts
and instructions. For both evaluations, you first need matching input data.
Please follow the instructions in the **input_data** folder. Finally, the
**paper_plots** folder contains scripts to produce some of the evaluation plots
in the paper.

## Python environment

For the simulation and lab experiments, you need certain Python packages (as
well as additional tools described in the corresponding READMES). We recommend
to install the Python packages in a virtual environment, e.g., using the
following commands:

```
mkdir .venv
python3 -m venv .venv/magnifier
source .venv/magnifier/bin/activate
pip install -e "."
```

## Changelog

* 2023.04.20: initial version
