#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-andersen-spec
#SBATCH --nodes=1
#SBATCH --cpus-per-node=50
#SBATCH --exclusive
#SBATCH --cpu-freq=highm1
#SBATCH --constraint=56c
#SBATCH --mem=240G
#SBATCH --time=48:00:00
#SBATCH --array=0-149
#SBATCH -o slurm-log/output.%a.out # STDOUT
set -euo pipefail

SELF=./run-slurm.sh

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
    --offset=$((SLURM_ARRAY_TASK_ID * 50)) --limit=50 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release \
    --statsdir statistics/release \
    --jlm-opt "$JLM_PATH/build-release/jlm-opt" \
    --benchmarkIterations 50 \
    --timeout 86000 \
    -j 25 || true

./benchmark.py \
    --offset=$((SLURM_ARRAY_TASK_ID * 50)) --limit=50 \
    --llvmbin "$(llvm-config-18 --bindir)" \
    --builddir build/release-anf \
    --statsdir statistics/release-anf \
    --jlm-opt "$JLM_PATH/build-release-anf/jlm-opt" \
    --benchmarkIterations 50 \
    --timeout 86000 \
    -j 25
