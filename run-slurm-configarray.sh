#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-andersen-spec
#SBATCH --cpus-per-task=4
#SBATCH --cpu-freq=highm1
#SBATCH --constraint=56c
#SBATCH --mem=40G
#SBATCH --time=24:00:00
#SBATCH --array=0-69
#SBATCH -o slurm-log/output-%j-config-%a.out # STDOUT
set -euo pipefail

SELF=./run-slurm-configarray.sh

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
    --offset=$TASK_INDEX --limit=1 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release-anf \
    --statsdir statistics/release-anf \
    --jlm-opt "$JLM_PATH/build-release-anf/jlm-opt" \
    --jlmExactConfig=$SLURM_ARRAY_TASK_ID \
    --configSweepIterations 50 \
    --timeout 86000 \
    -j1
