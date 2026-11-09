#!/usr/bin/env python3
import sys
import subprocess
import tempfile

"""
Drop-in replacement for a compiler driver like clang.
For compilation of single C files (-c), the command is converted into a clang + opt + jlm-opt pipeline.
It matches 1:1 with the pipeline defined in ./benchmark.py for sroa-raw with all techniques enabled.
"""

def main():
    pass

if __name__ == "__main__":
    main()
