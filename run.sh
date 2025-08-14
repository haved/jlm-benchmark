#!/usr/bin/env bash
set -eu

# This script is designed for running the full evaluation of PIP
# It should be run in the container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# Timeout in seconds given to each invocation of jlm-opt
TIMEOUT=20
# Timeout given to files that timed out, and got promoted to getting separate jlm-opt invocations per configuration
TIMEOUT_SEPARATE_CONFIGS=1200
# The explicit pointee files can run for a really long time, but we only really care about the fastest one finishing
TIMEOUT_SEPARATE_CONFIGS_ANF=200

# Uncomment the below line to create sources.json and sources-redist2017.json from scratch
# [Requires cpu2017.tar.xz in sources/programs/]
# RECREATE_SOURCES_JSON="yes"

# Restore the artifact back to a clean state by using ./run.sh clean
# The exception is if you have made any changes to sources.json
if [[ "${1-}" == "clean" ]]; then
    echo "Deleting old builds of jlm-opt"
    just clean-jlm-builds

    echo "Deleting extracted sources"
    just sources/programs/clean-all-free

    echo "Removing all result files from previous runs of jlm-opt"
    just purge

    exit 0
fi

echo "Building jlm-opt"
# Build the jlm-opt binary, both using impicit pointees and explicit pointees (ANF)
just build-release
just build-release-anf


# Prepare the source folder
pushd sources
if [[ -v RECREATE_SOURCES_JSON ]]; then
    # Only if the user has specifically requested it do we trace the building all the benchmarks

    echo "Performing full builds of all benchmarks, and tracing compilation commands"
    just build-all-benchmarks

    echo " - Creating sources.json and sources-redist2017.json"
    just create-sources-json

    SOURCES_JSON="sources/sources.json"
else
    # The default option: only extract benchmarks, unless building is necessary

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


echo "Starting benchmarking of jlm-opt"
set -x

# Benchmark on all files in sources.json.
# Try solving the constraint graph 50 times per config, but only try for a limited time per file
just benchmark-release     "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=50" || true
just benchmark-release-anf "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=50" || true

# Try again on files that timed out, but only try 1 time per configuration this time
just benchmark-release     "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=1" || true
just benchmark-release-anf "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT} --configSweepIterations=1" || true

# Try again on files that timed out, but only try 1 time per configuration this time
just benchmark-release     "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT_SEPARATE_CONFIGS} --separateConfigurations 138" || true
just benchmark-release-anf "--sources=$SOURCES_JSON -j$(nproc) --timeout=${TIMEOUT_SEPARATE_CONFIGS} --separateConfigurations 70" || true
