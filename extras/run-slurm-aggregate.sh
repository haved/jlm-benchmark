#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-stats-aggregate
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=1
#SBATCH --constraint=56c
#SBATCH --mem=20G
#SBATCH --time=48:00:00
#SBATCH -o slurm-log/aggregate-%j.out # STDOUT
set -euo pipefail

SELF=./run-slurm-aggregate.sh

if [ -z ${APPTAINER_NAME+x} ]; then
    # re-execute this script in an apptainer
    exec apptainer exec "$APPTAINER_CONTAINER" "$SELF" "$@"
fi

just aggregate
