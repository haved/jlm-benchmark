#!/usr/bin/env bash
set -eu

# This script is designed for running the full evaluation of PIP
# It should be run in the container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# TODO: Parse arguments


if [[ -v CLEAN_JLM_BUILDS ]]; then
    echo "Deleting old builds of jlm-opt"
    just clean-jlm-builds
fi
echo "Building jlm-opt"
# Build the jlm-opt binary, both using impicit pointees and explicit pointees (ANF)
just build-release
just build-release-anf

# Prepare source folders
pushd sources
if [[ -v RETRACE_ALL_BENCHMARK_BUILDS ]]; then
    # Only if the user has specifically requested it do we build all the benchmarks

    echo "Performing full builds of all benchmarks, and tracing compilation commands"
    just build-all-benchmarks

    echo " - Creating sources-raw.json"
    just create-sources-raw-json

    echo " - Processing sources-raw.json"
    just process-sources-json

    SOURCES_JSON="sources/sources.json"
else
    # The default option: only extract benchmarks, and do not rebuild them

    echo "Extracting open source programs"
    just programs/extract-all-free

    if [ -f programs/cpu2017.tar.xz ]; then
        echo " - Found cpu2017.tar.xz, using it for all the SPEC2017 benchmarks"
        just programs/extract-cpu2017
        SOURCES_JSON="sources/sources.json"
    else
        echo " - Did not find cpu2017.tar.xz, using the redist2017 sources instead"
        just programs/extract-redist2017
        SOURCES_JSON="sources/sources-redist2017.json"
    fi
fi
popd

# Remove all files from previous benchmarking runs
if [[ -v CLEAN_JLM_RUNS ]]; then
    echo "Removing all files from previous runs of jlm-opt"
    just purge
fi

echo "Starting benchmarking of jlm-opt"
set -x

# Benchmark on all files in sources.json.
# Try solving the constraint graph 50 times per config, but only try for 20 seconds per file
just benchmark-both "--sources=$SOURCES_JSON -j$(nproc) --timeout=20 --configSweepIterations=50"

# Try again on files that timed out, but only try 1 time per configuration this time
just benchmark-both "--sources=$SOURCES_JSON -j$(nproc) --timeout=20 --configSweepIterations=1"
