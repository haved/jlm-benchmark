#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=pip-artifact
#SBATCH --nodes=1
#SBATCH --tasks-per-node=32
#SBATCH --cpus-per-task=1
#SBATCH --cpu-freq=highm1
#SBATCH --constraint=56c
#SBATCH --mem=128G
#SBATCH --time=48:00:00
#SBATCH -o slurm-log/output.%a.out # STDOUT
set -euo pipefail

exec apptainer exec "$APPTAINER_CONTAINER" ./run.sh "$@"
