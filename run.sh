#!/usr/bin/env bash
set -eux

# This script is designed for running the full evaluation of PIP
# It should be in a container created from the provided Dockerfile,
# or on a system with all of the same dependencies installed.
# The current directory must be mounted into the Docker container.

# Build the jlm-opt binary, both with using impicit pointees and explicit pointees (ANF)
just clean-jlm-builds
just build-release
just build-release-anf

# If you want to play with jlm-opt yourself, the binary can be found in jlm/build-release/jlm-opt

# Prepare source folders by extracting tarballs
cd sources
just programs/extract-all-free
if [ -f programs/cpu2017.tar.xz ]; then
    echo "Found cpu2017.tar.xz, using it for all the SPEC2017 benchmarks"
    just programs/extract-cpu2017
else
    echo "Did not find cpu2017.tar.xz, using the redist2017 sources instead"
    just programs/extract-redist2017
fi

# If you want to build and trace the original compilation of the benchmarks yourself,
# and create your own sources.json files, you can use the below commands
# just create-sources-raw-json
# just process-sources-json
