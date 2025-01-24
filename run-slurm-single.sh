#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-andersen-single
#SBATCH --cpus-per-task=1
#SBATCH --constraint=56c
#SBATCH --mem=128G
#SBATCH --time=8-0
#SBATCH -o slurm-log/single.%a.out # STDOUT
set -euo pipefail

SELF=./run-slurm-single.sh

if [ -z ${APPTAINER_NAME+x} ]; then
    # re-execute this script in an apptainer
    exec apptainer exec "$APPTAINER_CONTAINER" "$SELF" "$@"
fi

# Default JLM_PATH, but let the .env file override it
JLM_PATH="jlm"
if [ -f .env ]; then
    source .env
fi

if [ -z ${BENCHMARK_ANF+x} ]; then
./benchmark.py \
    --offset "${SLURM_ARRAY_TASK_ID}" \
    --limit 1 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release \
    --statsdir statistics/release \
    --jlm-opt "$JLM_PATH/build-release/jlm-opt" \
    --benchmarkIterations 10 \
    --timeout 86000
else
    ./benchmark.py \
    --offset "${SLURM_ARRAY_TASK_ID}" \
    --limit 1 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release-anf \
    --statsdir statistics/release-anf \
    --jlm-opt "$JLM_PATH/build-release-anf/jlm-opt" \
    --benchmarkIterations 2 \
    --timeout 86000
fi
