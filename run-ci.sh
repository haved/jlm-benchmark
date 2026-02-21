#!/usr/bin/env bash
set -eu

# This script is used for unpacking benchmarks and compiling benchmarks using jlm-opt.

# Check if llvm-config of correct version exists in the PATH
# and if found set the LLVM_BIN to llvm's bindir
LLVM_VERSION=18
LLVM_CONFIG_BIN=llvm-config-${LLVM_VERSION}
if command -v ${LLVM_CONFIG_BIN} &> /dev/null
then
	LLVM_BIN=$(${LLVM_CONFIG_BIN} --bindir)
else
	LLVM_BIN=""
fi

# Check if we can find jlm-opt
if command -v ../../build/jlm-opt &> /dev/null
then
	JLM_OPT=../../build/jlm-opt
else
	JLM_OPT=""
fi

# Used for executing only specific benchmarks
EXTRA_BENCH_OPTIONS=""

# Used to determine which benchmarks to extract
EXTRACT_ALL=true
EXTRACT_SPEC=false
EXTRACT_EMACS=false
EXTRACT_GHOSTSCRIPT=false
EXTRACT_GDB=false
EXTRACT_SENDMAIL=false
SOURCES_JSON=""

# Execute benchmarks in parallel by default
if [[ "$OSTYPE" == "darwin"* ]]; then
  PARALLEL_INVOCATIONS=`sysctl -n hw.ncpu`
else
  PARALLEL_INVOCATIONS=`nproc`
fi

function usage()
{
	echo "Usage: ./run-ci.sh [OPTION]"
	echo ""
	echo "  --parallel #THREADS   The number of threads to run in parallel."
	echo "                        Default=[${PARALLEL_INVOCATIONS}]"
	echo "  --jlm-opt             Path to the jlm-opt binary."
	echo "                        Default=[${JLM_OPT}]"
	echo "  --llvm-bin            Path to the llvm binary directory."
	echo "                        Default=[${LLVM_BIN}]"
	echo "  --polybench           Compile polybench."
	echo "  --spec                Extract and compile SPEC."
	echo "  --emacs               Extract and compile emacs."
	echo "  --ghostscript         Extract and compile ghostscript."
	echo "  --gdb                 Extract and compile gdb."
	echo "  --sendmail            Extract and compile sendmail."
	echo "  --clean               Delete extracted sources and build files."
	echo "  --help                Prints this message and stops."
}

while [[ "$#" -ge 1 ]] ; do
	case "$1" in
		--clean)
			echo "Deleting extracted sources"
			just sources/programs/clean-all
			echo "Removing all result files from previous runs of jlm-opt"
			just purge
			exit 1
			;;
		--parallel)
			shift
			PARALLEL_INVOCATIONS=$1
			shift
			;;
		--jlm-opt)
			shift
			JLM_OPT=$(readlink -m "$1")
			shift
			;;
		--llvm-bin)
			shift
			LLVM_BIN=$(readlink -m "$1")
			shift
			;;
		--polybench)
			EXTRA_BENCH_OPTIONS="--filter=polybench"
			EXTRACT_ALL=false
			shift
			;;
		--spec)
			EXTRA_BENCH_OPTIONS="--filter=500\\.perlbench|502\\.gcc|507\\.cactuBSSN|525\\.x264|526\\.blender|538\\.imagick|544\\.nab|557\\.xz"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--perlbench)
			EXTRA_BENCH_OPTIONS="--filter=500\\.perlbench"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--gcc)
			EXTRA_BENCH_OPTIONS="--filter=502\\.gcc"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--cactuBSSN)
			EXTRA_BENCH_OPTIONS="--filter=507\\.cactuBSSN"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--x264)
			EXTRA_BENCH_OPTIONS="--filter=525\\.x264"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--blender)
			EXTRA_BENCH_OPTIONS="--filter=526\\.blender"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--imagick)
			EXTRA_BENCH_OPTIONS="--filter=538\\.imagick"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--nab)
			EXTRA_BENCH_OPTIONS="--filter=544\\.nab"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--xz)
			EXTRA_BENCH_OPTIONS="--filter=557\\.xz"
			EXTRACT_SPEC=true
			EXTRACT_ALL=false
			shift
			;;
		--emacs)
			EXTRA_BENCH_OPTIONS="--filter=emacs"
			EXTRACT_EMACS=true
			EXTRACT_ALL=false
			shift
			;;
		--ghostscript)
			EXTRA_BENCH_OPTIONS="--filter=ghostscript"
			EXTRACT_GHOSTSCRIPT=true
			EXTRACT_ALL=false
			shift
			;;
		--gdb)
			EXTRA_BENCH_OPTIONS="--filter=gdb"
			EXTRACT_GDB=true
			EXTRACT_ALL=false
			shift
			;;
		--sendmail)
			EXTRA_BENCH_OPTIONS="--filter=sendmail"
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
if [ ${EXTRACT_ALL} = true ] || [ ${EXTRACT_SPEC} = true ]; then
	echo "Extracting SPEC redistributable sources."
	just programs/extract-redist2017
	SOURCES_JSON="sources/sources-redist2017.json"
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
popd

# Ensure Ctrl-C quits immediately, without starting the next command
function sigint() {
    echo "${0}: Aborted by user action (SIGINT)"
    exit 1
}
trap sigint SIGINT

echo "Starting benchmarking of jlm-opt"
set +e

mkdir -p build statistics
echo "./benchmark.py --jlm-opt ${JLM_OPT} --llvmbin ${LLVM_BIN} --sources=sources/sources-redist2017.json -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/ci --statsdir statistics/ci"
./benchmark.py --jlm-opt ${JLM_OPT} --llvmbin ${LLVM_BIN} --sources=sources/sources-redist2017.json -j${PARALLEL_INVOCATIONS} ${EXTRA_BENCH_OPTIONS:-} --regionAwareModRef --builddir build/ci --statsdir statistics/ci

exit 0
