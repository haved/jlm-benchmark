#!/usr/bin/env python3
import sys
import os
import subprocess
import tempfile

"""
Drop-in replacement for a compiler driver like clang.
For compilation of single C files (-c), the command is converted into a clang + opt + jlm-opt pipeline.
It matches 1:1 with the pipeline defined in ./benchmark.py for sroa-raw with all techniques enabled.

The script finds jlm-opt using the environment variable JLM_OPT_PATH = <path/to/jlm-opt>.
If it does not exist, "${JLM_PATH}/build-release/jlm-opt" is tried instead.

clang and opt are found using "${CLANG_PATH}" and "${OPT_PATH}", defaulting to "clang-18" and "opt-18"
"""

def get_paths():
    clang = os.environ.get("CLANG_PATH", "clang-18")
    opt = os.environ.get("OPT_PATH", "opt-18")
    jlm_opt = os.environ.get("JLM_OPT_PATH", None)

    if jlm_opt is None:
        jlm_path = os.environ.get("JLM_PATH", None)
        if jlm_path is None:
            raise ValueError("Neither JLM_OPT_PATH nor JLM_PATH are defined")

        jlm_opt = os.path.join(jlm_path, "build-release/jlm-opt")

    if "/" in jlm_opt and not jlm_opt.startswith("/"):
        raise ValueError(f"JLM_OPT_PATH / JLM_PATH needs to be an aboslute path. Got: {jlm_opt}")

    return clang, opt, jlm_opt

CLANG, OPT, JLM_OPT = get_paths()

# Flags skipped for C compilation
SKIP_FLAGS = [
    "-O",
    "-O0",
    "-O1",
    "-O2",
    "-O3",
    "-Os",
    "-Oz",
    "-Ofast"
    ]

# When standalone, the next argument belongs to it
C_FLAGS_WITH_ARGUMENTS = [
    "-I",
    "-include",
    "-D",
    "-o",
    "-x",
    "-MF",
    "-MT",
]

def extract_flags_and_positional(args):
    """
    Extracts positional arguments and flags, placing them in two lists

    For single options, returns them as a string.
    Options with arguments, like -o file and -o=file, are extracted to tuples ("-o", "file")
    """
    flags = []
    positional = []
    flag_in_progress = None
    for arg in args:
        if arg.startswith("-"):
            if arg in C_FLAGS_WITH_ARGUMENTS:
                flag_in_progress = arg
                continue

            if "=" in arg:
                pos = arg.find("=")
                flags.append((arg[:pos], arg[pos+1:]))
                continue

            # Just a regular flag
            flags.append(arg)
        elif flag_in_progress is not None:
            flags.append((flag_in_progress, arg))
            flag_in_progress = None
        else:
            positional.append(arg)

    if flag_in_progress is not None:
        raise ValueError(f"command ended with option that takes an argument: {args}")

    return flags, positional

def extract_flag_with_argument(flags, flag_to_find):
    """
    Finds a flag if it exists, removes it, and extracts its value.
    For flags without arguments, the value is True for found.
    Flags not found yield None

    :param flag_to_find:

    Returns (value/True/None, flags left)
    """
    if not isinstance(flag_to_find, list):
        flag_to_find = [flag_to_find]

    flags_left = []
    value_found = []

    for flag in flags:
        if isinstance(flag, tuple):
            key, value = flag
            if key in flag_to_find:
                value_found.append(value)
                continue
        else:
            if flag in flag_to_find:
                value_found.append(true)
                continue

        flags_left.append(flag)

    if len(value_found) > 1:
        # This is fine if they all have the same value
        if any(x != value_found[0] for x in value_found):
            raise ValueError(f"Multiple different values provided for flag(s) {flag_to_find}: {value_found}")
    if value_found:
        return value_found[0], flags_left

    return None, flags_left

def execute_intercepted_command(input_file, flags):
    """
    Convert the input_file to an .o file optimized by jlm-opt
    """

    output_file, flags = extract_flag_with_argument(flags, ["-o", "--output"])

    clang_command = [CLANG, "-S", "-emit-llvm", ""]


def execute_original_command(args):
    """
    Just passes the command directly to clang
    """
    command = [CLANG, *args]
    p = subprocess.run(command)
    return p.returncode

def main():
    args = sys.argv[1:]
    if "-c" not in args:
        return execute_original_command(args)

    flags, positional = extract_flags_and_positional(args)

    if len(positional) > 1:
        extracted, _ = extract_flag_with_argument(flags, ["-o", "--output"])
        if extracted is not None:
            raise ValueError("Multiple input files is not supported when -o is supplied")

    for input_file in positional:
        returncode = execute_intercepted_command(input_file, flags)
        if returncode != 0:
            return returncode

    # Everything went well
    return 0

if __name__ == "__main__":
    returncode = main()
    sys.exit(returncode)
