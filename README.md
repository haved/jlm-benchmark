# Artifact for PIP paper

## Setup
If you have a copy of SPEC2017, place it inside the `sources/programs/` folder.
It should be a file called `cpu2017.tar.xz` containing files like `install.sh`.

If SPEC2017 is not provided, the run script will automatically use the included `redist2017` folder instead,
which contains redistributable sources from SPEC2017.
This will skip the `505.mcf` benchmark, and use a subset of the sources on `500.perlbench`,
but all the other benchmarks should give the same results. See `sources/README.md` for details.

The artifact assumes you have at least 8 physical cores, and 32 GB of RAM.
If you have more, then you can modify the `PARALLEL_INVOCATIONS` variable at the top of `run.sh`,
to make evaluation go faster. The default is 8.

## Running
The easiest way to run this artifact is using the provided `Dockerfile`.

Build a docker image with all the needed dependencies using
``` sh
docker build -t pip-2026-image .
```

Before running benchmarks, configure your CPU to run at a stable frequency where it does not boost or throttle, e.g., using
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```

Then mount the current directory and run the script `./run.sh` inside a Docker container using
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/artifact pip-2026-image ./run.sh
```

The `run.sh` script does the following:

 - Builds the included jlm compiler in the `jlm/` folder. It builds both the `release` target, and the `release-anf` target.
   ANF means "Andersen No Flags", and corresponds to all configurations with the Explicit Pointee representation.
   The finished binaries are located in `jlm/build-release/jlm-opt` and `jlm/build-release-anf/jlm-opt`, respectively.
   
 - Extracts the 4 free and open source benchmark programs. The tarballs in `sources/programs/` are extracted in place.
   Some of the benchmarks are also configured and built, because the build process creates some header files that are necessary for compiling.
   
 - Depending on whether or not SPEC2017 was provided, it will:
   - Extract `cpu2017.tar.xz`, using SPEC's own setup script.
   
   - Extract the subset of SPEC2017 that is available in `redistributed_sources/`.
   
 - Starts the actual benchmarking. This step has a progress counter that looks like `[394/7498] ...`.
   First it compiles all the C files from all the benchmarks into LLVM IR.
   Then it uses `jlm-opt` to perform points-to analysis on each IR file.
   
   The progress counter can be a bit misleading, because benchmarking runs 5 times:
    1. First it tries to analyze all the files using each IP Configuration 50 times, but with a `TIMEOUT`.
    2. Then it tries to analyze all the files using each EP Configuration 50 times, also with a `TIMEOUT`.
    3. Then it re-tries solving files that timed out in (1.), but using each IP Configuration just 1 time. This can not time out.
    4. Then it re-tries solving files that timed out in (2.), but using each EP Configuration just 1 time. It times out after `TIMEOUT_MEDIUM_ANF` seconds.
    5. Lastly it re-tries solving files that time out in (4.), using only the `EP+OVS+WL(LRF)+OCD` configuration. This can not time out.

 - Finally it aggregates the statistics produced from each points-to analysis and precision evaluation, into CSV files in `statistics-out/`.
   These are used to create plots and tables in the `results/` folder.

In the paper, each configuration has been run 50 times per file without any timeouts.
For the artifact, the timeouts ensure that evaluation can be done in a reasonable amount of time.
To make the results less noisy, the timeout and/or analysis iteration count variables in `run.sh` can be increased.
An archive of the `statistics-out` folder used in the paper can be found in `results-in-2026-paper/`.

### Restarting evaluation
If the `run.sh` script is for some reason aborted, it can be restarted and resume roughly where it left off.

If you wish to reset all progress made by the script and start from scratch, you can pass `clean` to the run script like so:
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/artifact pip-2026-image ./run.sh clean
```
This will remove all builds of `jlm-opt`, all extracted benchmarks, and any results from previous runs.

### Running without docker
If you install all dependencies mentioned in the `Dockerfile`, you can also run without docker.
However, some dependencies may be located in different locations on your system.
To ensure building the benchmarks will still work, you can configure and build all benchmarks from scratch and trace the C compiler invocations using
``` sh
./run.sh create-sources-json
```

Doing this requires having your own copy of `cpu2017.tar.xz` in `sources/programs/`.

This will create a new `sources/sources.json` file, which contains the C compiler invocations involved in building each benchmark program.

If you prefer Apptainer over docker, there is an Apptainer definition file in the `extras/` folder that is equivalent to the `Dockerfile`.
It can be used without re-creating `sources.json`.

## Results
After running, tables and figures are written to the `results/` folder.
Tables and figures from the paper are `.txt` and `.pdf` files,
while numbers mentioned in the text of the paper can be found in the `.log` files.

Numbers based on measured runtimes will probably differ from those in the paper, based on the performance of the system you run on.
The overall ratios between configurations should still be roughly the same, however.

Precision numbers, file size numbers and the number of pointees should be almost identical,
but may differ by a very small amount due to the open source benchmarks configuring themselves slightly differently on different systems.

## Performing custom experiments
If you wish to perform other experiments, there are multiple options for customizing the process:
 - Create your own `sources/sources.json` file containing compilation commands for
   any C program, and pass it to the `./benchmark.py` script.
   You may want to use the scripts in `sources/`, or just do it by hand for small programs.
   
 - Change timeouts and number of iterations at the top of `run.sh`.
   
 - You can modify the `./benchmark.py` script to add extra flags to `clang`, `opt` and/or `jlm-opt`.

 - You can use the `jlm-opt` binary under `jlm/build-release/jlm-opt` directly on any LLVM IR file made with LLVM 18.
    - Use the flags `--AAAndersenAgnostic --print-andersen-analysis` to dump statistics.
    - Use the flag `--print-aa-precision-evaluation` to do precision evaluation against LLVM's BasicAA.
    - Use `-s .` to place the output statistics in the current folder.
    - Set the environment variable `JLM_ANDERSEN_DUMP_SUBSET_GRAPH` to print the constraint graph to stdout in GraphViz dot format, before and after solving the constraint set.

 - The source code of the Anderen-style analysis is located in `jlm/jlm/llvm/opt/alias-analyses/`:
  - `Andersen.{cpp,hpp}` converts program IR into constraint variables and constraints.
  - `PointerObjectSet.{cpp,hpp}` contains the algorithms for solving constraint sets
  - `AliasAnalysis.{cpp,hpp}` contains alias analyses, including the one using the PointsToGraph from Andersen.
  - `PrecisionEvaluator.{cpp,hpp}` produces precision metrics from the different alias analyses
 
