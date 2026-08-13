#!/usr/bin/env bash
set -eu

# This script is used for unpacking benchmarks and compiling benchmarks using jlm-opt.

# source .env if it exists
if [ -f .env ]; then
    source .env
fi

# Assign defaults if not already specified as environment variables.
# These can also be overwritten using --options
LLVM_CONFIG="${LLVM_CONFIG:-llvm-config-18}"
JLM_OPT="${JLM_OPT:-${JLM_PATH:-jlm}/build-release/jlm-opt}"

# Execute benchmarks in parallel by default
if [[ "$OSTYPE" == "darwin"* ]]; then
  PARALLEL_INVOCATIONS=`sysctl -n hw.ncpu`
else
  PARALLEL_INVOCATIONS=`nproc`
fi

# Options added to the final ./benchmark.py invocation
EXTRA_BENCH_OPTIONS=""

# Used to determine which benchmarks to extract
EXTRACT_ALL=true
EXTRACT_SPEC=false
EXTRACT_EMACS=false
EXTRACT_GHOSTSCRIPT=false
EXTRACT_GDB=false
EXTRACT_SENDMAIL=false
EXTRACT_EMBENCH=false

# If true, a real copy of cpu2017 is used, instead of the included redist2017
FULL_SPEC=false
# Path to sources json file containing benchmark compilation descriptions
# This can be overwritten from the .env file, to use sources-arch.json
SOURCES_JSON=${SOURCES_JSON:-"sources/sources.json"}

# Parameters for deciding what tasks the script should perform
BUILD_JLM=false
DRY_RUN=false
CREATE_JSON=false

# If running in CI, perform a standard benchmark to test that everything is working.
# This makes it easier to keep the CI up to date with the main branch of this repository.
RUNNING_IN_CI=false

function usage()
{
    echo "Usage: ./run.sh [task] [options]"
    echo ""
    echo "Tasks:"
    echo "    run               The default. Extract and compile benchmarks"
    echo "    create-json       Build all benchmarks to re-create sources.json. Implies --full-spec"
    echo "    clean-runs        Remove build output and statistics from running benchmarks, and exit."
    echo "    clean-jlm         Remove the build(s) of jlm-opt, and exit."
    echo "    purge             Perform the above removals, remove all extracted benchmark programs, and exit."
    echo "    help / --help     Print this message and exit."
    echo ""
    echo "Options to the run task:"
    echo "  --parallel <threads>  The number of threads to run in parallel."
    echo "                        Default=[${PARALLEL_INVOCATIONS}]"
    echo "  --jlm-opt <path>      Specify the path to jlm-opt."
    echo "                        Default=[${JLM_OPT}]"
    echo "  --llvm-config <path>  Path to the llvm config binary."
    echo "                        Default=[${LLVM_CONFIG}]"
    echo "  --build-jlm           Clone the jlm repository and build debug and release."
    echo "                        Uses the given jlm-opt path to decide directory."
    echo "  --full-spec           Use the full version of SPEC instead of redist2017. Requires cpu2017.tar.xz."
    echo "  --dry-run             Do all setup except actually compiling benchmarks."
    echo "  --do-validation       Execute validation scripts after compiling benchmarks."
    echo "  --ci                  Perform a benchmark run suitable for CI and exit with its status code."
    echo ""
    echo "  Optional filters:     (or none to select all)"
    echo "    SPEC CPU 2017 benchmarks (redist or full)"
    echo "      --spec            Compile all supported SPEC benchmarks."
    echo "      --perlbench       Compile 500.perlbench."
    echo "      --gcc             Compile 502.gcc."
    echo "      --mcf             Compile 505.mcf (not in redist)."
    echo "      --cactuBSSN       Compile 507.cactuBSSN."
    echo "      --x264            Compile 525.x264."
    echo "      --blender         Compile 526.blender."
    echo "      --imagick         Compile 538.imagick."
    echo "      --nab             Compile 544.nab."
    echo "      --xz              Compile 557.xz."
    echo "    Other benchmark suites"
    echo "      --embench         Compile the Embench IoT suite."
    echo "      --polybench       Compile the Polybench suite."
    echo "    Open source programs"
    echo "      --emacs           Compile emacs."
    echo "      --gdb             Compile gdb."
    echo "      --ghostscript     Compile ghostscript."
    echo "      --sendmail        Compile sendmail."
	echo ""
}

# Helper function for making sure no options have been given to a task that doesn't take them
assert_no_options() {
    if [[ "$#" -gt 1 ]] ; then
        echo "$0: error: the task '${1}' does not take any options. Unknown option: ${2}" >&2
        exit 1
    fi
}

# Figure out what task we are performing first, if given
case "${1-}" in
    run)
        # This is the default task
        shift
        ;;
    create-json)
        assert_no_options "$@"
        FULL_SPEC=true
        CREATE_JSON=true
        shift
        ;;
    clean-runs)
        assert_no_options "$@"
        echo "Removing build output, statistics and results from runs"
        just clean-runs
        exit 0
        ;;
    clean-jlm)
        assert_no_options "$@"
        echo "Removing build of jlm-opt"
        just clean-jlm-builds
        exit 0
        ;;
    purge)
        assert_no_options "$@"
        "$0" clean-runs
        "$0" clean-jlm
        echo "Deleting extracted sources"
        just sources/programs/clean-all
        exit 0
        ;;
    help)
        usage >&2
        exit 0
        ;;
esac

# Process options for the run task
while [[ "$#" -ge 1 ]] ; do
    case "$1" in
        --parallel)
            shift
            PARALLEL_INVOCATIONS="$1"
            shift
            ;;
        --jlm-opt)
            shift
            JLM_OPT="$(readlink -m "$1")"
            shift
            ;;
        --llvm-config)
            shift
            LLVM_CONFIG="$1"
            shift
            ;;
        --build-jlm)
            BUILD_JLM=true
            shift
            ;;
        --full-spec)
            FULL_SPEC=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --do-validation)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --do-validation"
            shift
            ;;
        --ci)
            RUNNING_IN_CI=true
            shift
            ;;
        # Filter for all of SPEC 2017
        --spec)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=5\\d\\d\\."
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        # Invividual SPEC 2017 benchmark filters
        --perlbench)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=500\\.perlbench"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --gcc)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=502\\.gcc"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --mcf)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=505\\.mcf"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --cactuBSSN)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=507\\.cactuBSSN"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --x264)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=525\\.x264"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --blender)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=526\\.blender"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --imagick)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=538\\.imagick"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --nab)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=544\\.nab"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        --xz)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=557\\.xz"
            EXTRACT_SPEC=true
            EXTRACT_ALL=false
            shift
            ;;
        # Other benchmark suites
        --embench)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=embench"
            EXTRACT_EMBENCH=true
            EXTRACT_ALL=false
            shift
            ;;
        --polybench)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=polybench"
            EXTRACT_ALL=false
            shift
            ;;
        # Open source benchmark filters
        --emacs)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=emacs"
            EXTRACT_EMACS=true
            EXTRACT_ALL=false
            shift
            ;;
        --gdb)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=gdb"
            EXTRACT_GDB=true
            EXTRACT_ALL=false
            shift
            ;;
        --ghostscript)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=ghostscript"
            EXTRACT_GHOSTSCRIPT=true
            EXTRACT_ALL=false
            shift
            ;;
        --sendmail)
            EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --filter=sendmail"
            EXTRACT_SENDMAIL=true
            EXTRACT_ALL=false
            shift
            ;;
        --help|*)
            usage >&2
            exit 1
            ;;
    esac
done

# Prepare the benchmarks
pushd sources

# If we have requested full spec
if [[ ${FULL_SPEC} = true ]]; then
   # Check that the tarball is in place
   if [ ! -f programs/cpu2017.tar.xz ]; then
       echo "error: missing file 'sources/programs/cpu2017.tar.xz'".
       exit 1
   fi
   EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --full-spec"
fi

# Instead of benchmarking jlm-opt, the user has requested to build all benchmarks to re-create sources.json
if [[ ${CREATE_JSON} = true ]]; then
    echo "Performing full builds of all benchmarks, and tracing compilation commands"
    just build-all-benchmarks

    echo " - Creating sources.json"
    just create-sources-json

    exit 0
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_SPEC} = true ]; then
    echo "Extracting SPEC ."
    if [ ${FULL_SPEC} = true ]; then
        just programs/extract-cpu2017
    else
        just programs/extract-redist2017
    fi
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_EMACS} = true ]; then
    echo "Extracting Emacs sources."
    just programs/extract-emacs
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_GHOSTSCRIPT} = true ]; then
    echo "Extracting ghostscript sources."
    just programs/extract-ghostscript
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_GDB} = true ]; then
    echo "Extracting gbd sources."
    just programs/extract-gdb
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_SENDMAIL} = true ]; then
    echo "Extracting gbd sources."
    just programs/extract-sendmail
fi

if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_EMBENCH} = true ]; then
    echo "Extracting embench sources."
    just programs/extract-embench
fi
popd

# Build the jlm-opt binary if requested
if [[ ${BUILD_JLM} = true ]]; then

    if [[ "${JLM_OPT}" = */build*/jlm-opt ]]; then
        # Remove the build-*/jlm-opt part of the jlm-opt path to find the jlm path
        export JLM_PATH="${JLM_OPT%/build*/jlm-opt}"
    else
        echo "Unable to extract a jlm path from the jlm-opt path (${JLM_OPT}). Aborting."
        exit 1
    fi

    echo "Cloning and building jlm in location: ${JLM_PATH}"
    just clone-jlm
    just build-release
    just build-debug
fi

# Check that the jlm-opt binary exists
if [[ ! -f "${JLM_OPT}" ]]; then
    echo "error: jlm-opt binary does not exist: ${JLM_OPT}"
    echo "hint: use --build-jlm to clone and build jlm in ${JLM_PATH}"
    exit 1
fi

# Extract the LLVM bindir
LLVM_BIN="$(${LLVM_CONFIG} --bindir || true)"
if [[ -z "${LLVM_BIN}" ]]; then
    echo "Unable to extract --bindir from ${LLVM_CONFIG}"
    exit 1
fi

if [ ${DRY_RUN} = true ]; then
    EXTRA_BENCH_OPTIONS="${EXTRA_BENCH_OPTIONS:-} --dry-run"
fi

# Ensure Ctrl-C quits immediately, without starting the next command
function sigint() {
    echo "${0}: Aborted by user action (SIGINT)"
    exit 1
}
trap sigint SIGINT

echo "Starting benchmarking of jlm-opt"
mkdir -p build statistics

# Enable echoing commands to print the benchmark.py invocations
set -x

# When running in CI we want a standard invocation that rarely changes,
# with an exit code indicating success or failure
if [ ${RUNNING_IN_CI} = true ]; then
    ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" --sources="${SOURCES_JSON}" \
        -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
        --regionAwareModRef --jlm-name ci
    exit $?
fi

# The benchmarking invocations below change frequently

# For testing with asserts (slow)
#./benchmark.py --jlm-opt="../jlm/build-debug/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --jlm-name debug
#exit 0

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --builddir build/jlm --statsdir statistics/jlm \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --builddir build/jlm --statsdir statistics/raware \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --builddir build/jlm --statsdir statistics/raware \
#    || true

#JLM_ENABLE_SVF_PTGAA=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --builddir build/jlm --statsdir statistics/ptgaa \
#    || true

#JLM_ENABLE_SVF_PTGAA=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --builddir build/jlm --statsdir statistics/ptgaa \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --optSroa --regionAwareModRef --builddir build/sroa --statsdir statistics/sroa-raware \
#    || true

#USE_OLD_UNCREACHABLE_CHECK=1 USE_ALT_UNCREACHABLE_CHECK=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --noStrictAliasing --optSroa --pre-jlm-name sroa \
#    --regionAwareModRef --jlm-name sroa-raware-both

#USE_OLD_UNCREACHABLE_CHECK=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --noStrictAliasing --optSroa --pre-jlm-name sroa \
#    --regionAwareModRef --jlm-name sroa-raware-old

#USE_ALT_UNCREACHABLE_CHECK=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --noStrictAliasing --optSroa --pre-jlm-name sroa \
#    --regionAwareModRef --jlm-name sroa-raware-alt


./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
    --noStrictAliasing --optSroa --pre-jlm-name sroa \
    --regionAwareModRef --jlm-name sroa-raware

./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
    --noStrictAliasing --optSroaGvn --pre-jlm-name sroa-gvn \
    --regionAwareModRef --jlm-name sroa-gvn-raware

exit 0

JLM_ENABLE_SVF_PTGAA=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
    --noStrictAliasing --optSroa --pre-jlm-name sroa \
    --jlm-name sroa-ptgaa

./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
    --noStrictAliasing --optSroa --pre-jlm-name sroa \
    --jlm-name sroa

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --optSroaGvn --regionAwareModRef --builddir build/gvn --statsdir statistics/gvn-raware \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --optSroaGvn --aggressiveGvn --builddir build/gvn-aggressive --statsdir statistics/gvn-aggressive-raware \
#    || true

./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
    --noStrictAliasing --clangOs --pre-jlm-name clang-Os \
    --regionAwareModRef --jlm-name clang-Os-raware

exit 0

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --clangO3 --builddir build/clang-O3 --statsdir statistics/clang-O3-raware \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --optMem2reg --regionAwareModRef --builddir build/mem2reg --statsdir statistics/mem2reg-raware \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --builddir build/jlm --statsdir statistics/jlm-aggressive-localaa \
#    || true

#JLM_ENABLE_SVF_PTGAA=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --builddir build/jlm --statsdir statistics/jlm-ptgaa \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --clangOs --builddir build/clang-Os --statsdir statistics/clang-Os-raware-aggressive-localaa \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --clangOs --builddir build/clang-Os --statsdir statistics/clang-Os \
#    || true

#./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --clangOs --builddir build/clang-Os --statsdir statistics/clang-Os-aggressive-localaa \
#    || true

#JLM_ENABLE_SVF_PTGAA=1 ./benchmark.py --jlm-opt="${JLM_OPT}" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --clangOs --builddir build/clang-Os --statsdir statistics/clang-Os-ptgaa \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --clangOs --optOs --builddir build/clang-Os-opt-Os --statsdir statistics/clang-Os-opt-Os \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --optOs --builddir build/opt-Os --statsdir statistics/opt-Os \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --optPreGvn --builddir build/opt-preGvn --statsdir statistics/opt-preGvn \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --optWithGvn --builddir build/opt-withGvn --statsdir statistics/opt-withGvn \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --clangO3 --builddir build/clang-O3 --statsdir statistics/clang-O3 \
#    || true

#./benchmark.py --jlm-opt="${JLM_PATH}/build-release/jlm-opt" --llvmbin="${LLVM_BIN}" \
#    --sources="${SOURCES_JSON}" -j="${PARALLEL_INVOCATIONS}" ${EXTRA_BENCH_OPTIONS:-} \
#    --regionAwareModRef --optMem2reg --builddir build/opt-m2r --statsdir statistics/opt-m2r \
#    || true

# Finally run some data aggregation
just aggregate
# Also try running and printing some analysis
just analyze-all
