# jlm benchmarking repository

## Initial setup
If you have a copy of SPEC2017, place it inside the `sources/programs/` folder.
It should be a file called `cpu2017.tar.xz` containing files like `install.sh`.

If SPEC2017 is not provided, the run script will automatically use the included `redist2017` folder instead,
which contains redistributable sources from SPEC2017.
This will skip the `505.mcf` benchmark, and use a subset of the sources on `500.perlbench`,
but all the other benchmarks should give the same results. See `sources/README.md` for details.

## Configuring the benchmarking

### Path to jlm
Be default the benchmarking setup clones `jlm` inside the benchmark repository.
If you wish to specify a different path to `jlm`, create a file called `.env`
containing the alternative path, e.g.:
```
JLM_PATH=../jlm
```
Note that this will not work when running with docker containers, unless `jlm/` is mounted at the given path.

### Parallel invocations of jlm-opt
Inside `run.sh` you can set the variable `PARALLEL_INVOCATIONS` to configure how many invocations of `jlm-opt` are started in parallel.

### Extra options to `benchmark.py`
Inside `run.sh` you can modify the variable `EXTRA_BENCH_OPTIONS` to pass arguments to the `benchmark.py` script.
Here you can specify things like filters on which benchmarks to include, or timeouts for `jlm-opt` invocations.

When running your own experiments, you should add new command line arguments inside `benchmark.py`,
and then trigger them from `run.py`, either using `EXTRA_BENCH_OPTIONS`, or by passing them in directly.

## Running with Docker
The easiest way to run the benchmarks is using the provided `Dockerfile`.

Build a docker image with all the needed dependencies using
``` sh
docker build -t jlm-benchmark-image .
```

Before running benchmarks, configure your CPU to run at a stable frequency where it does not boost or throttle, e.g., using
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```

Then mount the current directory and run the script `./run.sh` inside a Docker container using
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/benchmark jlm-benchmark-image ./run.sh
```

The `run.sh` script does the following:
   
 - Extracts the open source benchmark programs. The tarballs in `sources/programs/` are extracted in place.
   Some of the benchmarks are also configured and built, because the build process creates some header files that are necessary for compiling.
   
 - Depending on whether or not SPEC2017 was provided, it will:
   - Extract `cpu2017.tar.xz`, using SPEC's own setup script.
   
   - Extract the subset of SPEC2017 that is available in `redistributed_sources/`.
   
 - Clones the jlm compiler
   
 - Builds the jlm compiler
   
 - Starts the actual benchmarking

## Restarting benchmarking
If the `run.sh` script is for some reason aborted, it can be restarted and resume roughly where it left off.

If you wish to reset all progress made by the script and start from scratch, you can pass `clean` to the run script like so:
``` sh
docker run -it --mount type=bind,source="$(pwd)",target=/benchmark jlm-benchmark-image ./run.sh clean
```
This will remove all builds of `jlm-opt`, all extracted benchmarks, and any results from previous runs.

## Running without docker
If you install all dependencies mentioned in the `Dockerfile`, you can run without docker.
However, some dependencies may be located in different locations on your system.
This will affect the compilation commands, so the file `sources/sources.json` will need to be re-made.
See sources/README.md for details.

If you prefer Apptainer over docker, there is an Apptainer definition file in the `extras/` folder that is equivalent to the `Dockerfile`.
It can be used without re-creating `sources.json`.

### Running across SLURM nodes
The SLURM setup uses Apptainer, so build the image first, using the apptainer definition file in the `extras/` folder.
``` sh
apptainer build --fakeroot jlm-benchmark.sif extras/jlm-benchmark.def
```

Before benchmarking, make sure you delete any old statistics and logs.
```sh
apptainer exec jlm-benchmark.sif just purge
rm -rf slurm-log
```

Then make sure sources are extracted and `jlm-opt` is built using:
``` sh
apptainer exec jlm-benchmark.sif ./run.sh dry-run
```

Then run `extras/run-slurm.sh` like so:
```sh
mkdir -p statistics build
APPTAINER_CONTAINER=jlm-benchmark.sif sbatch extras/run-slurm.sh
```

