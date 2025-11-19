#!/usr/bin/env bash
set -eu

# This script is used for unpacking benchmarks, compiling jlm-opt, and compiling benchmarks using jlm-opt.
# It should be run in the container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# Run multiple jlm-opt invocations at once during benchmarking
# You should probably have a least have 4GB RAM and one physical core per invocation.
# Default: 8, to run on a machine with 8 physical cores and 32 GB of RAM.
PARALLEL_INVOCATIONS=8

# If you wish to pass extra options to all the benchmarking invocations, uncomment this variable.
# EXTRA_BENCH_OPTIONS='--filter="505\\.mcf|544\\.nab|525\\.x264"'
# |507\\.cactuBSSN|538\\.imagick"'
# EXTRA_BENCH_OPTIONS='--timeout 600'
EXTRA_BENCH_OPTIONS='--filter="polybench"'

# Restore the artifact back to a clean state by using ./run.sh clean
# If you have made any changes to sources.json, they are not restored
if [[ "${1-}" == "clean" ]]; then
    echo "Deleting old builds of jlm-opt"
    just clean-jlm-builds

    echo "Deleting extracted sources"
    just sources/programs/clean-all

    echo "Removing all result files from previous runs of jlm-opt"
    just purge

    exit 0
fi

# Use ./run.sh dry-run to do all setup except actually compiling benchmarks
if [[ "${1-}" == "dry-run" ]]; then
    echo "Setting --dry-run flag"
    EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --dry-run"
fi

# Prepare the benchmarks in the sources folder
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

# Download jlm if it is not already cloned
just clone-jlm

# Build the jlm-opt binary
echo "Building jlm-opt"
just build-debug
just build-release

# Ensure Ctrl-C quits immediately, without starting the next command
function sigint() {
    echo "${0}: Aborted by user action (SIGINT)"
    exit 1
}
trap sigint SIGINT

echo "Starting benchmarking of jlm-opt on all files in ${SOURCES_JSON}"
set +e
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware"
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --useMem2reg --builddir build/raware --statsdir statistics/m2r"

export JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST=1
export JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST=1
export JLM_DISABLE_OPERATION_SIZE_BLOCKING=1
export JLM_DISABLE_CONSTANT_MEMORY_BLOCKING=1
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware-no-tricks"

unset JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware-only-dead-alloca-blocklist"
export JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST=1

unset JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware-only-non-reentrant-alloca-blocklist"
export JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST=1

unset JLM_DISABLE_OPERATION_SIZE_BLOCKING
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware-only-operation-size-blocking"
export JLM_DISABLE_OPERATION_SIZE_BLOCKING=1

unset JLM_DISABLE_CONSTANT_MEMORY_BLOCKING
just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/raware --statsdir statistics/raware-only-constant-memory-blocking"
export JLM_DISABLE_CONSTANT_MEMORY_BLOCKING=1

just benchmark-release "--sources=$SOURCES_JSON -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --agnosticModRef --builddir build/raware --statsdir statistics/agnostic"
