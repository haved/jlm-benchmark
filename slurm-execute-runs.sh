#!/usr/bin/env bash
#SBATCH --partition=CPUQ
#SBATCH --account=share-ie-idi
#SBATCH --job-name=jlm-benchmark
#SBATCH --nodes=1
#SBATCH --tasks-per-node=1
#SBATCH --cpus-per-task=4
#SBATCH --cpu-freq=highm1
#SBATCH --constraint=56c
#SBATCH --mem=64G
#SBATCH --time=48:00:00
#SBATCH --array=0-399
#SBATCH -o slurm-log/output.%a.out # STDOUT
set -euo pipefail

# Find the script in runs/ corresponding to the array job number

RUNS_FOLDER="runs"

RUNS_SCRIPT="$(ls "${RUNS_FOLDER}" | sort | sed -n "${SLURM_ARRAY_TASK_ID}p")"
exec apptainer exec "$APPTAINER_CONTAINER" "bash" "${RUNS_FOLDER}/${RUNS_SCRIPT}"
