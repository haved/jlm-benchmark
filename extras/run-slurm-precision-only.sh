#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-andersen-spec
#SBATCH --nodes=1
#SBATCH --tasks-per-node=16
#SBATCH --cpus-per-task=1
#SBATCH --constraint=56c
#SBATCH --mem=40G
#SBATCH --time=06:00:00
#SBATCH --array=0-468
#SBATCH -o slurm-log/precision.%a.out # STDOUT
set -euo pipefail

SELF=./run-slurm-precision-only.sh

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
    --offset=$((SLURM_ARRAY_TASK_ID * 16)) --limit=16 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release \
    --statsdir statistics/release \
    --jlm-opt "$JLM_PATH/build-release/jlm-opt" \
    -j 8 || true
