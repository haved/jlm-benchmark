# Extras folder

This folders contains parts of the original benchmarking setup.
It was done on a SLURM cluster, and ran each configuration 50 times on each file, even though that could take days,
and in most cases would have absolutely no effect on the results. (The EP Oracle only cares about the fastest configuration for each C file).

This folder is provided purely as an extra to look at.
It contains:
 - `jlm-benchmark.sif` the Apptainer Image description file used to run benchmarks
 - A bunch of SLURM scripts for running jobs, and extra scripts for re-running ones that timed out.
 
See also the file `statistics-out-may21.tar.gz` in the `results-in-2026-paper` directory,
which contains the `statistics-out` folder that was used to create the runtime results.

The rest of this README is the original README used while working on the paper

-----------------------------------------------------------------------

# Andersen with flags - Benchmarking and results
This repository is used for running benchmarks of the Andersen analysis in jlm, and analyzing the resulting statistics.

Note that you will need a distribution of the file `cpu2017.tar.xz`, not provided here.

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
just build-release
just build-release-anf
```

# Setting up benchmark programs

## Downloading and setting up open source benchmarks
Go into the folder `sources/` and execute the build job to prepare all source files.

```sh
cd sources
just build-all-free
```

## Unpacking SPEC2017
If you have a copy of `cpu2017.tar.xz`, go into `sources/spec2017/` and unpack it using the following command:
``` sh
cd sources/spec2017
just install-cpu2017 <path/to/cpu2017.tar.xz>
just run-cpu2017
```

## Creating sources.json
The file `sources/sources.json` contains an index of all C files that will be included in the bechmarking.
Create this file using

``` sh
cd sources/
just create-sources-json 
```

## Verifying you have the programs
From the root of this repository, run
``` sh
just benchmark-release --list
```

If everything went well, it should print out

``` sh
13 benchmarks:
  505.mcf                12 C files
  544.nab                20 C files
  525.x264               36 C files
  500.perlbench          69 C files
  557.xz                 90 C files
  538.imagick            97 C files
  sendmail-8.18.1       137 C files
  emacs-29.4            148 C files
  gdb-15.2              262 C files
  507.cactuBSSN         347 C files
  502.gcc               387 C files
  526.blender          1005 C files
  ghostscript-10.04.0  1139 C files
```

# Running benchmarks
For running, you have the option of distributing the work across a SLURM cluster.
This is almost necessary when doing multiple iterations, but if one iteration is fine you can do it locally.

## Running without SLURM
Before bechmarking, you should try to make the CPU clock as stable as possible, e.g. using
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```

Benchmarking all C files with both the release and release-anf targets of `jlm-opt` can be done using
``` sh
# Optional: clean up any existing benchmark results first
just purge

just benchmark-release "--configSweepIterations 1 -j8 --timeout=1000"
just benchmark-release-anf "--configSweepIterations 1 -j8 --timeout=1000"
```
This will only test each configuration once per file, yet still take a long time.
The `-j8` can be changed to use more worker threads.

By passing `--timeout=1000`, the maximum amount of time any `jlm-opt` process gets to use is limited to 1000 seconds.
When finished, all tasks that timed out will be listed, and the script will exit with status code 1.
Keep in mind that omitting the slowest files will skew the results.

Running the benchmark script again will skip all tasks that have already finished, unless the `--eager` flag is passed. Running with `--dry-run` will quickly print the set of tasks left to be done.

Extra flags can be passed to run only a subset of tasks. See `--help` for details.

## Running on SLURM
In order to benchmark each configuration multiple times in a reasonable amount of time,
the work has to be split across a SLURM cluster.
`sbatch` is not available inside the apptainer, so run it from outside.
The array job divides all the work into separate jobs.
Each job will start its own container using the specified apptainer image.

``` sh
mkdir -p build statistics
rm -rf slurm-log
APPTAINER_CONTAINER="jlm-benchmark.sif" sbatch run-slurm.sh
```

### Restarting files that timed out
You can check if any of the jobs timed out by doing a `--dry-run` as described above, which may look something like:
```
$ just benchmark-release --dry-run
Skipping 7359 tasks due to laziness, leaving 1
[1/1] (6099) jlm-opt ghostscript-10.04.0+base_gdevp14.c (dry-run)

$ just benchmark-release-anf --dry-run
Skipping 7357 tasks due to laziness, leaving 3
[1/3] (4681) jlm-opt 526.blender+blender_bin_source_blender_makesrna_intern_rna_nodetree_gen.c (dry-run)
[2/3] (4701) jlm-opt 526.blender+blender_bin_source_blender_makesrna_intern_rna_scene_gen.c (dry-run)
[3/3] (4731) jlm-opt 526.blender+blender_bin_source_blender_makesrna_intern_rna_userdef_gen.c (dry-run)
```

You can start these particular missing jobs again with a lower number of benchmark iterations using
``` sh
APPTAINER_CONTAINER="jlm-benchmark.sif" sbatch --array=6099 run-slurm-single.sh
APPTAINER_CONTAINER="jlm-benchmark.sif" BENCHMARK_ANF=1 sbatch --array=4681,4701,4731 run-slurm-single.sh
```

### Spreading configurations across SLURM jobs
If the dry-run output for `benchmark-release-anf` contains a task like

```
[1/12] (1041) jlm-opt emacs-29.4+src_xdisp.c (dry-run)
```

You can distribute the configs across the cluster, one config per job, using

``` sh
APPTAINER_CONTAINER="jlm-benchmark.sif" TASK_INDEX=1041 sbatch run-slurm-configarray.sh
```

This lets you quickly analyze the file with each EP config, 50 times each, to remove noise.
The SLURM script has a timeout of only 1 hour, as the results only need the fastest EP to finish.
Otherwise it would run for days.

# Analysis
## Aggregating statistics
The benchmark script dumps statistics for individual alias analysis passes to `statistics/<target>`.
The processing of all these statistics `.log` files is dumped to `statistics-out/`.

```sh
just aggregate
```

This can also be done in a SLURM-job if desired:

``` sh
APPTAINER_CONTAINER="jlm-benchmark.sif" sbatch run-slurm-aggregate.sh
```

## Alternative: Extracting aggregated statistics
The repository also contains aggregated statistics from a complete run. Extract them using

``` sh
just extract-aggregated
```

## Analysis scripts
Inside the `analysis/` directory, there are some scripts for doing extra analysis and plotting graphs from the aggregated statistics. Run them all using:
``` sh
just analyze-all
```

The resulting plots are placed in `results/`
