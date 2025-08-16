# Artifact for PIP paper

## Setup
If you have a copy of SPEC2017, i.e., the file `cpu2017.tar.xz`,
place it inside the `sources/programs/` folder.

If it is not provided, the run script will automatically use the included `redist2017` folder instead,
which contains redistributable sources from SPEC2017.
This will skip the `505.mcf` benchmark, but should otherwise provide the same results.

## Running
The easiest way to run this artifact is using the provided Dockerfile.

Build a docker image with all the needed dependencies using
``` sh
docker build -t pip-2026-image .
```

Before running benchmarks, configure your CPU to run at a stable frequency where it does not boost or throttle.
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```

Then mount the current directory and run the script `./run.sh` inside the Docker environment using
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/artifact pip-2026-image ./run.sh
```

The script builds the `jlm-opt` compiler, extracts the benchmarks, and passes all C files to `jlm-opt` for analysis. The benchmarks are not actually built, only analyzed.

Each invocation of `jlm-opt` is given a timeout.
The script first tries to analyze each C file using all 208 configurations 50 times each, like done in the paper.
Files that time out are re-tried, using each analysis configuration once.
If the `jlm-opt` compiler with Expiclit Pointee (EP) representation *still* times out,
it will be invoked one last time where it only uses the `EP+OVS+WL(LRF)+OCD` configuration.

To make the results more stable, the timout and/or iteration count variables in `run.sh` can be increased.

### Resetting execution
If the `run.sh` script is aborted, it can be restarted and resume roughly where it left off.
To reset all progress made by the script, execute `./run.sh clean`. 

### Running without docker
If you install all dependencies mentioned in the `Dockerfile`, you can also run without docker.
However, some dependencies may be located in different locations.
To ensure building the benchmarks will work, you can configure and build all benchmarks from scratch and trace the C compiler invocations using
``` sh
./run.sh create-sources-json
```

Doing this requires bringing your own copy of `cpu2017.tar.xz`.

This will create a new `sources/sources.json` file, which contains the C compiler invocations involved in building each benchmark program.

If you prefer Apptainer over docker, there is an equivalent Apptainer definition file in the `extras/` folder.

## Results
Once building is done, results are aggregated and analyzed, producing tables and figures in the `results/` folder. They correspond to tables and figures from the paper. The produced log files contain the numbers mentioned in the text of the paper.

Numbers based on measured runtimes will probably differ from those in the paper, based on the system you run on. The overall ratios between configuration should still be roughly the same, however.
For the paper, each C file was analyzed 50 times per configuration, while the artifact sometimes reduces this number in the interest of time. The resulting plots might therefore look more noisy.

Precision numbers, file size numbers and the number of pointees should be almost identical, but may differ by a miniscule amount due to the open source benchmarks including slightly different files on different systems.

## Performing custom experiments
If you wish to perform other experiments, there are multiple options for customizing the process:
 - Create your own `sources/sources.json` file containing compilation commands for
   any C program, and pass it to the `./benchmark.py` script.
   You may want to use the scripts in `sources/`, or just do it by hand for small programs.
   
 - How long timeouts are, and which steps are executed, can be configured at the top of `run.sh`.
   
 - You can modify the the `./benchmark.py` script to add extra flags to `clang`, `opt` and/or `jlm-opt`.

 - You can use the `jlm-opt` binary under `jlm/build-release/jlm-opt` directly on any LLVM IR file made with LLVM 18.
 
 - The source code of the Anderen-style analysis is located in `jlm/jlm/llvm/opt/aa/`:
  - `Andersen.{cpp,hpp}` converts program IR into constraint variables and constraints.
  - `PointerObjectSet.{cpp,hpp}` contains the algorithms for solving constraint sets
  - `AliasAnalysis.{cpp,hpp}` contains alias analyses, including the one using the PointsToGraph from Andersen.
  - `PrecisionEvaluator.{cpp,hpp}` produces precision metrics from the different alias analyses
 
