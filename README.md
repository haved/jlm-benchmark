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
docker run -it --mount type=bind,source="$(pwd)",target=/mnt pip-2026-image ./run.sh
```

The script builds the `jlm-opt` compiler, extracts the benchmarks, and passes all C files to `jlm-opt` for analysis.

Each invocation of `jlm-opt` is given a timeout. You can configure this timeout with `--timeout <seconds>`, but do be aware that some files can be extremely slow to solve with certain configurations.

The script first tries to analyze each C file using all 208 configurations 50 times each, like done in the paper.

Files that time out are re-tried with fewer iterations, and eventually run with separate `jlm-opt` invocations per configuration.

## Results


## Performing custom experiments
If you wish to perform other experiments, there are multiple options for customizing the process:
 - Create your own `sources/sources.json` file containing compilation commands for
   any C program, and pass it to the `./benchmark.py` script.
   You may want to use the scripts in `sources/`, or just do it by hand for small programs.
   
 - You can modify the the `./benchmark.py` script to add extra flags to `clang`, `opt` and/or `jlm-opt`.

 - You can use the `jlm-opt` binary under `jlm/build-release/jlm-opt` directly on any LLVM IR file made with LLVM 18. 
