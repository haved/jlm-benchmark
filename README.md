# jlm benchmarking repository

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

## Running without docker
If you install all dependencies mentioned in the `Dockerfile`, you can run without docker.
However, some dependencies may be located in different locations on your system.
To ensure building the benchmarks will still work, you can configure and build all benchmarks from scratch and trace the C compiler invocations using
``` sh
./run.sh create-sources-json
```

Doing this requires having your own copy of `cpu2017.tar.xz` in `sources/programs/`.

This will create a new `sources/sources.json` file, which contains the C compiler invocations involved in building each benchmark program.

If you prefer Apptainer over docker, there is an Apptainer definition file in the `extras/` folder that is equivalent to the `Dockerfile`.
It can be used without re-creating `sources.json`.

### Running across SLURM nodes
First make sure the release build of `jlm-opt` has been built.

```sh
apptainer exec jlm-benchmark.sif just build-release
```

Make sure you delete any old statistics
```sh
apptainer exec jlm-benchmark.sif just purge
rm -rf slurm-log
```

Then run `extras/run-slurm.sh` like so:
```sh
mkdir -p build statistics
APPTAINER_CONTAINER=jlm-benchmark.sif sbatch extras/run-slurm.sh
```

## Running with Docker
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

 - Builds the jlm compiler
   
 - Extracts the open source benchmark programs. The tarballs in `sources/programs/` are extracted in place.
   Some of the benchmarks are also configured and built, because the build process creates some header files that are necessary for compiling.
   
 - Depending on whether or not SPEC2017 was provided, it will:
   - Extract `cpu2017.tar.xz`, using SPEC's own setup script.
   
   - Extract the subset of SPEC2017 that is available in `redistributed_sources/`.
   
 - Starts the actual benchmarking

### Restarting evaluation
If the `run.sh` script is for some reason aborted, it can be restarted and resume roughly where it left off.

If you wish to reset all progress made by the script and start from scratch, you can pass `clean` to the run script like so:
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/artifact pip-2026-image ./run.sh clean
```
This will remove all builds of `jlm-opt`, all extracted benchmarks, and any results from previous runs.
