#!/usr/bin/env bash
set -eu

# This script is designed for running the full evaluation of PIP
# It should be run in the container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# Timeout in seconds given to each invocation of jlm-opt
TIMEOUT=20
# Timeout given to files that timed out, and got promoted to getting separate jlm-opt invocations per configuration
# It is still okay if some of these time out, as the oracle only cares about the fastest config per file
TIMEOUT_SEPARATE_CONFIGS=200

# Uncomment the below line to delete jlm-opt builds before starting
# CLEAN_JLM_BUILD="yes"

# Uncomment the below line to delete results from previous jlm-opt runs
# CLEAN_JLM_RUNS="yes"

# Uncomment the below line to create sources.json and sources-redist2017.json from scratch
# [Requires cpu2017.tar.xz in sources/programs/]
# RETRACE_ALL_BENCHMARK_BUILDS="yes"

if [[ -v CLEAN_JLM_BUILD ]]; then
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
    # Only if the user has specifically requested it do we build all the benchmarks again

    echo "Performing full builds of all benchmarks, and tracing compilation commands"
    just build-all-benchmarks

    echo " - Creating sources.json and sources-redist2017.json"
    just create-sources-json

    SOURCES_JSON="sources/sources.json"
else
    # The default option: only extract benchmarks, and do not rebuild them

    echo "Extracting open source programs"
    just programs/extract-all-free

    echo "Extracting SPEC2017"
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

# Remove all files from previous benchmarking runs if requested
if [[ -v CLEAN_JLM_RUNS ]]; then
    echo "Removing all files from previous runs of jlm-opt"
    just purge
fi

echo "Starting benchmarking of jlm-opt"
set -x

# Benchmark on all files in sources.json.
# Try solving the constraint graph 50 times per config, but only try for a limited time per file
just benchmark-both "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=50"

# Try again on files that timed out, but only try 1 time per configuration this time
just benchmark-both "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=1"

# Try again on files that timed out, but only try 1 time per configuration this time
just benchmark-release "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT_SEPARATE_CONFIGS} --separateConfigurations 138"
just benchmark-release-anf "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT_SEPARATE_CONFIGS} --separateConfigurations 70"
