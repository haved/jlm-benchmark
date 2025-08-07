# Artifact for PIP paper

## Setup
If you have a copy of SPEC2017, i.e., the file `cpu2017.tar.xz`,
place it inside the `sources/programs/` folder.

If it is not provided, the run script will automatically use 

## Running
The easiest way to run this artifact is using the provided Dockerfile.

Build a docker image with all the needed dependencies using
``` sh
docker build -t pip-2026-image .
```

Then mount the current directory and run the script `./run.sh` inside the Docker environment using
``` sh
docker run \
-it \
--name pip-2026-artifact \
--mount type=bind,source="$(pwd)",target=/mnt \
pip-2026-image \
./run.sh
```

## Performing custom experiments
If you wish to perform other experiments, there are multiple options for customizing the process:
 - Create your own `sources/sources.json` file containing compilation commands for
   any C program, and pass it to the `./benchmark.py` script
 - You can modify the the `./benchmark.py` script to add extra flags to `clang`, `opt` and/or `jlm-opt`.
 - You can use the `jlm-opt` binary under `jlm/build-release/jlm-opt` directly on any LLVM IR file made with LLVM 18.
