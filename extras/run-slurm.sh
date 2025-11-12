#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-benchmark
#SBATCH --nodes=1
#SBATCH --tasks-per-node=16
#SBATCH --cpus-per-task=1
#SBATCH --cpu-freq=highm1
#SBATCH --constraint=56c
#SBATCH --mem=40G
#SBATCH --time=48:00:00
#SBATCH --array=0-468
#SBATCH -o slurm-log/output.%a.out # STDOUT
set -euo pipefail

SELF=./extras/run-slurm.sh

if [ -z ${APPTAINER_NAME+x} ]; then
    # re-execute this script in an apptainer
    exec apptainer exec "$APPTAINER_CONTAINER" "$SELF" "$@"
fi

# Set a default JLM_PATH, but let the .env file override it
JLM_PATH="jlm"
if [ -f .env ]; then
    source .env
fi

COMMON_BENCH_OPTIONS="--offset=$((SLURM_ARRAY_TASK_ID * 16)) --limit=16 \
    --llvmbin $(llvm-config-18 --bindir) \
    --jlm-opt $JLM_PATH/build-release/jlm-opt \
    --builddir build/raware \
    -j8"

set +e
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-all-tricks
./benchmark.py ${COMMON_BENCH_OPTIONS} --useMem2reg --statsdir statistics/m2r

export JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST=1
export JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST=1
export JLM_DISABLE_OPERATION_SIZE_BLOCKING=1
export JLM_DISABLE_CONSTANT_MEMORY_BLOCKING=1
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-no-tricks

unset JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-only-dead-alloca-blocklist
export JLM_DISABLE_DEAD_ALLOCA_BLOCKLIST=1

unset JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-only-non-reentrant-alloca-blocklist
export JLM_DISABLE_NON_REENTRANT_ALLOCA_BLOCKLIST=1

unset JLM_DISABLE_OPERATION_SIZE_BLOCKING
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-only-operation-size-blocking
export JLM_DISABLE_OPERATION_SIZE_BLOCKING=1

unset JLM_DISABLE_CONSTANT_MEMORY_BLOCKING
./benchmark.py ${COMMON_BENCH_OPTIONS} --regionAwareModRef --statsdir statistics/raware-only-constant-memory-blocking
export JLM_DISABLE_CONSTANT_MEMORY_BLOCKING=1
