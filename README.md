# jlm benchmarking repository

## Initial setup
Make sure all the dependencies listed in `apt-install-dependencies.sh` are installed.
This is most easily done by creating a distrobox for benchmarking.

### Creating a Distrobox
Distrobox is the easiest way of running benchmarks on your own system, as it handles mounting folders for you.
Install `podman` and `distrobox`.

The first time you want to run, build the container image, and use it to create a distrobox.
``` sh
podman build --squash -t jlm-benchmark-image .
distrobox create jlm-benchmark-box --image jlm-benchmark-image
```

Now, whenever you want to run any of the benchmarking scripts, start by entering the distrobox
``` sh
distrobox enter jlm-benchmark-box
```

## CPU configuration
Before running benchmarks, configure your CPU to run at a stable frequency where it does not boost or throttle, e.g., using
``` sh
sudo cpupower frequency-set --min 3GHz --max 3GHz --governor performance
```
This command should *not* be run inside the distrobox.

## Running benchmarks
The script `run.sh` invokes the necessary commands for extracing benchmarks and compiling them.
It can also clone and build jlm, if requested.

By default, the script will use the included `redist2017` folder for SPEC2017.
It contains redistributable sources for most of the C benchmarks, but does not contain the `505.mcf` benchmark,
and uses a subset of the sources on `500.perlbench`.
All the other benchmarks should give the same results. See `sources/README.md` for details.

If you have a copy of SPEC2017, you can place it inside the `sources/programs/` folder.
It should be a file called `cpu2017.tar.xz` containing files like `install.sh`.
With it in place, you can pass `--full-spec` to the `./run.sh` script.

The `./run.sh` script takes options to filter which benchmark programs it compiles. See `--help`.

To check if the programs were compiled correctly, you can pass `--do-validation` to run some simple checks.

The `./run.sh` script can change frequently as different configurations are being tested.
To execute benchmarks with a "standard" configuration, add the `--ci` flag.

### Path to jlm
By default the `run.sh` script assumes that `jlm-opt` is located at `jlm/build-release/jlm-opt`.
A different path can be specified using `--jlm-opt <path>`.
This will also update the location where `jlm` is cloned and built, if using `--build-jlm`.

You can change the default location of `jlm` by creating an `.env` file containing:
```
JLM_PATH=../jlm
```

### Extra options to `benchmark.py`
Inside `run.sh` you can modify the variable `EXTRA_BENCH_OPTIONS` to pass arguments to the `benchmark.py` script.
Here you can specify things like filters on which benchmarks to include, or timeouts for `jlm-opt` invocations.

When running your own experiments, you should add new command line arguments inside `benchmark.py`,
and then trigger them from `run.sh`, either using `EXTRA_BENCH_OPTIONS`, or by manually changing the invocations at the bottom of the file.

## Restarting benchmarking
If the `run.sh` script is for some reason aborted, it can be restarted and resume roughly where it left off.

If you wish to reset all build progress, you can pass `--clean-runs` to the run script like so:
``` sh
./run.sh --clean-runs
```
This will remove all build output, statistics and processed results from previous runs.

If you want to delete builds of jlm, this can be done using `--clean-jlm`.

If you want to remove all of the above, in addition to all extracted benchmarks, this can be done using `--purge`.
Deleting the extracted benchmark programs means they will be extracted and re-configured on the next run,
which can be necessary if the environment has changed. This should be rare, however.

## Alternative ways of running

### Running with Docker
You can also use docker to run the scripts, but you have to manually mount folders.
``` sh
docker build -t jlm-benchmark-image .

docker run -u $(id -u):$(id -g) -it --mount type=bind,source="$(pwd)",target=/benchmark jlm-benchmark-image ./run.sh --build-jlm --ci
```

### Running without docker
If you install all dependencies listed in `apt-install-dependencies.sh`, you can run without docker.
However, some dependencies may be located in different locations if you are not running on Ubuntu 24.
This will affect the compilation commands, so the file `sources/sources.json` will need to be re-made.
See [[sources/README.md]] for details.

If you prefer Apptainer over docker, there is an Apptainer definition file in the `extras/` folder that is equivalent to the `Dockerfile`.
It can be used without re-creating `sources.json`.
See the README in the `extras/` folder for instructions.

### Running across SLURM nodes (a bit outdated)
There are some SLURM scripts in the `extras/` folder that can be used with Apptainer to spread work across SLURM nodes.


