#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-andersen-single
#SBATCH --cpus-per-task=1
#SBATCH --constraint=56c
#SBATCH --mem=32G
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

./benchmark.py \
    --offset "${SLURM_ARRAY_TASK_ID}" \
    --limit 2 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release \
    --statsdir statistics/release \
    --jlm-opt "$JLM_PATH/build-release/jlm-opt" \
    --benchmarkIterations 50
