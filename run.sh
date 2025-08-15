#!/usr/bin/env bash
set -eu

# This script is designed for running the full evaluation of PIP
# It should be run in the container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# Lets multiple jlm-opt invocations run at once.
# (To be safe, have a least have 4GB RAM per core)
PARALLEL_INVOCATIONS=8

# Timeout in seconds given to the first invocations of jlm-opt for each C file
# Invocations that time out are retried with a longer timeout and fewer repetitions
TIMEOUT=40

# When first attempting to analyze a C file, how many time should each configuration be used.
# Higher numbers give more stable results, but increase likelihood of timing out
CONFIG_COUNT_MANY=50

# If the last attempt timed out, how many times should each configuration be used instead
CONFIG_COUNT_FEW=1

# When running jlm-opt for EP configurations, we still have a timeout
TIMEOUT_MEDIUM_ANF=400
# If some of the jlm-opt invocations using EP representation still time out,
# we run one last time where weprioritize getting numbers for the EP+OVS+WL(LRF)+OCD configuration

# Restore the artifact back to a clean state by using ./run.sh clean
# If you have made any changes to sources.json, they are not restored
if [[ "${1-}" == "clean" ]]; then
    echo "Deleting old builds of jlm-opt"
    just clean-jlm-builds

    echo "Deleting extracted sources"
    just sources/programs/clean-all

    echo "Removing all result files from previous runs of jlm-opt"
    just purge

    echo "Removing progress keeper file"
    rm -rf .run.sh.progress

    exit 0
fi

echo "Building jlm-opt"
# Build the jlm-opt binary, both using impicit pointees and explicit pointees (ANF)
just build-release
just build-release-anf


# Prepare the source folder
pushd sources
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

# Instead of benchmarking jlm-opt, the user has requested to build all benchmarks to re-create sources.json
if [[ "${1-}" == "create-sources-json" ]]; then

    echo "Performing full builds of all benchmarks, and tracing compilation commands"
    just build-all-benchmarks

    echo " - Creating sources.json and sources-redist2017.json"
    just create-sources-json

    exit 0
fi
popd

echo "Starting benchmarking of jlm-opt on all files in ${SOURCES_JSON}"

# This file is used to avoid re-running jlm-opt invocations that timed out last time
touch .run.sh.progress

# Try solving the constraint graph many times per config, but only try for a limited time per file
if [[ $(< .run.sh.progress) -lt 1 ]]; then
    just benchmark-release     "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} --timeout=${TIMEOUT} --configSweepIterations=${CONFIG_COUNT_MANY}"
    echo 1 > .run.sh.progress
fi
if [[ $(< .run.sh.progress) -lt 2 ]]; then
    just benchmark-release-anf "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} --timeout=${TIMEOUT} --configSweepIterations=${CONFIG_COUNT_MANY} --skipPrecisionEvaluation"
    echo 2 > .run.sh.progress
fi

# Try again on files that timed out, but only try fewer times per configuration this time
if [[ $(< .run.sh.progress) -lt 3 ]]; then
    # For
    just benchmark-release     "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} --configSweepIterations=${CONFIG_COUNT_FEW}"
    echo 3 > .run.sh.progress
fi
if [[ $(< .run.sh.progress) -lt 4 ]]; then
    just benchmark-release-anf "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} --timeout=${TIMEOUT_MEDIUM_ANF} --configSweepIterations=${CONFIG_COUNT_FEW} --skipPrecisionEvaluation"
    echo 4 > .run.sh.progress
fi

if [[ $(< .run.sh.progress) -lt 5 ]]; then
    # Solve using one specific configuration to avoid taking forever
    just benchmark-release-anf "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} --exactConfiguration=35 --skipPrecisionEvaluation --jlmV=2"
    echo 5 > .run.sh.progress
fi

echo "Aggregating individual run statistics into tables"
just aggregate

echo "Analyzing the statistics tables to make the tables and figures from the paper"
just analyze-all
