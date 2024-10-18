# Andersen with flags - Benchmarking and results
This repository is used for running benchmarks of the Andersen analysis in jlm, and analyzing the resulting statistics.

Note that you will need a distribution of the file `cpu2017.tar.xz`, not provided here.

# Setup
First, clone this repository to a suitable location.

The machines used for running the bechmarks requires the following:
 - Has `llvm-18`/`clang-18`.
 - Can build and run the revision of `jlm-opt` specified in `justfile`.
 - Has Python 3 with `matplotlib` and `pandas` to run the benchmarks and plot the results.
 - Some steps use `just` as a command runner.

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

## Building jlm
By default, `jlm` is cloned and built in the folder `jlm/`, if it does not already exist.
If you want to use a different path, create a file called `.env` and add a line like so
```
# Use jlm folder parallel to the benchmark repository
JLM_PATH=../jlm
```

Cloning and checking out the correct revision of `jlm` is done using
``` sh
just checkout-jlm-revision
```

Once ready to build both the release and the release-anf targets of `jlm-opt`, run
``` sh
just build-jlm-opt
```

## Unpacking SPEC2017
Assuming `cpu2017.tar.xz` is available somewhere, unpack it using the following commands:
``` sh
cd sources/spec2017
just install-cpu2017 <path/to/cpu2017.tar.xz>
```

# Running benchmarks
Before bechmarking, you should try to make the CPU clock as stable as possible, e.g. using
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```

## Running without SLURM
Benchmarking all C files with both the release and release-anf targets of `jlm-opt` can be done using
``` sh
# Optional: clean up any existing benchmark results first
just purge

just benchmark-release -j8
just benchmark-release-anf -j8
```
This will only test each configuration once per file, yet still take a long time.
The `-j8` can be changed to use more workers.
Extra flags can be passed to run only a subset of tasks, and `--dry-run` can be used to print the tasks left to be done.

## Running on SLURM
In order to benchmark each configuration multiple times in a reasonable amount of time,
the work has to be split across a SLURM cluster.
`sbatch` is not available inside the apptainer, so run it from outside.
The array job divides all the work into separate jobs.
Each job will start its own container using the specified apptainer image.

``` sh
APPTAINER_CONTAINER="jlm-benchmark.sif" sbatch run-slurm.sh
```

# Analysis
## Aggregating statistics
The benchmark script dumps statistics for individual alias analysis passes to `statistics/<target>`.
The processing of these statistics is dumped to `statistics-out/<target>`.

```sh
just aggregate-both
```

## Analysis scripts
Inside the `analysis/` directory, there are some scripts for doing extra analysis and plotting graphs from the aggregated statistics. Run them all using:
``` sh
just analyze-all
```

The resulting plots are placed in `results/`
