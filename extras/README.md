# Extras folder

This folders contains parts of the original benchmarking setup.
It contains:
 - `jlm-benchmark.sif` the Apptainer Image description file used to run benchmarks
 - A bunch of SLURM scripts for running jobs, and extra scripts for re-running ones that timed out.

# Setup
First, clone this repository to a suitable location.

The machines used for running the bechmarks require the following:
 - Has `llvm-18`/`clang-18`.
 - Can build and run the revision of `jlm-opt` specified in `justfile`.
 - Has Python 3 with `matplotlib`, `seaborn` and `pandas`, to run the benchmarks and plot the results.
 - The steps below use `just` as a command runner.

The simplest way of getting everything set up is using the provided Apptainer image definition file.
If you want to install dependencies locally, see the commands in `jlm-benchmark.def`.

## Building Apptainer image
Create the apptainer image using:
``` sh
apptainer build --fakeroot jlm-benchmark.sif jlm-benchmark.def
```

The rest of the commands in this guide can then be run inside an apptainer shell:
``` sh
apptainer shell jlm-benchmark.sif
```

