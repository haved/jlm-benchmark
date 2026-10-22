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
#SBATCH --array=1-400
#SBATCH -o slurm-log/output.%a.out # STDOUT
set -euo pipefail

# Set a default JLM_PATH, but let the .env file override it
JLM_PATH="jlm"
if [ -f .env ]; then
    source .env
fi
export JLM_PATH
# On SLURM, place individual statistics files in the tmpfs, only keep aggregated
export TMP_STATS_DIR="/tmp/jlm-statistics"
# Make the slurm task delete its statistics folder afterwards
export CLEAN_TMP_STATS_DIR=1
# Avoid doing anything in parallel on SLURM
export PARALLEL_TASKS=1

# Find the script in runs/ corresponding to the array job number
RUNS_FOLDER="runs"
RUNS_SCRIPT="$(ls "${RUNS_FOLDER}" | sort | sed -n "${SLURM_ARRAY_TASK_ID}p")"
exec apptainer exec "$APPTAINER_CONTAINER" "bash" "${RUNS_FOLDER}/${RUNS_SCRIPT}"
