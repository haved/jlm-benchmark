set dotenv-load

# Set the default JLM_PATH environment variable, unless specified in .env
export JLM_PATH := env_var_or_default("JLM_PATH", "jlm")

# Use LLVM18 for processing benchmarks
llvm-bin := `llvm-config-18 --bindir`

# Compile jlm-opt using clang++ from the LLVM bindir, unless specified in .env
JLM_CXX := env_var_or_default("JLM_CXX", "clang++-18")
CXXFLAGS_DISABLE_WARNINGS := env_var_or_default("JLM_CXXFLAGS_DISABLE_WARNINGS", "")

default:
    @just --list

# Clone jlm into the JLM_PATH if it does not already exist
clone-jlm:
    #!/usr/bin/bash -eu
    if [[ ! -d {{JLM_PATH}} ]]; then
      echo "{{JLM_PATH}} not found, cloning from git!"
      git clone https://github.com/phate/jlm.git {{JLM_PATH}}
    fi

# Build the release and target of jlm-opt
build-release:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building release target"
    ./configure.sh --target release CXX={{JLM_CXX}} CXXFLAGS_DISABLE_WARNINGS={{CXXFLAGS_DISABLE_WARNINGS}}
    make jlm-opt -j`nproc`

# Build the release and target of jlm-opt
build-debug:
    #!/usr/bin/bash -eu
    cd {{JLM_PATH}}

    echo "Building debug target"
    ./configure.sh --target debug --enable-asserts CXX={{JLM_CXX}} CXXFLAGS_DISABLE_WARNINGS={{CXXFLAGS_DISABLE_WARNINGS}}
    make jlm-opt -j`nproc`

# Remove builds of jlm-opt
clean-jlm-builds:
    rm -rf {{JLM_PATH}}/build*

# Aggregate statistics from runs
aggregate:
    mkdir -p statistics-out
    ./analysis/aggregate-memstates.py --stats-in statistics --stats-out statistics-out

# Perform analysis and plotting on the aggregated statistics
analyze-all:
    [ -d statistics-out ] # This recipe only works if statistics-out exists
    mkdir -p results
    ./analysis/compare-memstates.py --stats statistics-out --out results

# Clean statistics-out and plotted results, but not raw statistics
clean-processed:
    rm -rf statistics-out
    rm -rf results

# Clean all build output, statistics and results
clean-runs: clean-processed
    rm -rf build
    rm -rf statistics
