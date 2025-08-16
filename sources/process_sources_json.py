#!/usr/bin/env python3

import argparse
import json
import re
import os
import sys

# Arguments that should be removed
IGNORED_ARGUMENTS = [
    "-O",
    "-O0",
    "-O1",
    "-O2",
    "-O3",
    "-Os",
    "-Oz",
    "-Ofast",
    "-c",
    "-g",
    "-g1",
    "-g2",
    "-g3",
    "-ggdb0",
    "-ggdb1",
    "-ggdb2",
    "-ggdb3",
    "--debug",
    "-gdwarf",
    "-gdwarf-1",
    "-gdwarf-2",
    "-gdwarf-3",
    "-gdwarf-4",
    "-gdwarf-5",
    "-gdwarf32",
    "-gdwarf64",
    "-gfull"
]

REPLACED_ARGUMENTS = {
    "-fstrict-flex-arrays": "-fstrict-flex-arrays=3"
}

# Files whose absolute path end in the following are excluded.
# This can be due to use of inline assembly, computed goto or special intrinsics
SKIPPED_FILES = [
    "emacs-29.4/src/bytecode.c",
    "emacs-29.4/src/json.c",
    "gdb-15.2/libiberty/sha1.c",
    "gdb-15.2/libbacktrace/mmap.c",
    "gdb-15.2/libbacktrace/dwarf.c",
    "gdb-15.2/libbacktrace/elf.c",
    "ghostscript-10.04.0/leptonica/src/bytearray.c",
    "ghostscript-10.04.0/leptonica/src/boxbasic.c",
    "ghostscript-10.04.0/leptonica/src/ccbord.c",
    "ghostscript-10.04.0/leptonica/src/compare.c",
    "ghostscript-10.04.0/leptonica/src/dnabasic.c",
    "ghostscript-10.04.0/leptonica/src/gplot.c",
    "ghostscript-10.04.0/leptonica/src/fpix1.c",
    "ghostscript-10.04.0/leptonica/src/numabasic.c",
    "ghostscript-10.04.0/leptonica/src/pix1.c",
    "ghostscript-10.04.0/leptonica/src/pixabasic.c",
    "ghostscript-10.04.0/leptonica/src/ptabasic.c",
    "ghostscript-10.04.0/leptonica/src/regutils.c",
    "ghostscript-10.04.0/leptonica/src/sarray1.c",
    "ghostscript-10.04.0/leptonica/src/writefile.c",
    "ghostscript-10.04.0/obj/gsromfs1.c"
]


def process_cfile(data):

    cfile = data["cfile"]
    ofile = data["ofile"]
    working_dir = data["working_dir"]
    arguments = data["arguments"]

    # Skip C++ files
    if cfile.endswith(".cpp"):
        return None

    # Skip files we have been told to skip
    if any(os.path.join(working_dir, cfile).endswith(s) for s in SKIPPED_FILES):
        return None

    # Replace and remove compiler arguments
    arguments = [REPLACED_ARGUMENTS.get(arg, arg) for arg in arguments if arg not in IGNORED_ARGUMENTS]

    # Replace build/build_base-paths from SPEC2017 with src/ to avoid relying on the build folder existsing
    working_dir = re.sub(r'/build/build_base_[^/]*', '/src', working_dir)

    # sendmail performs builds inside directories named after the linux kernel being used
    # Replace this subfolder by the top level sendmail
    if re.search(r'sendmail-8\.18\.1/obj[^/]*/', working_dir):
        working_dir = re.sub(r'/obj[^/]*', '', working_dir)
        # Also fix any include path that starts with ../
        arguments = [re.sub(r'^-I../', '-I', arg) for arg in arguments]

    return {
        "cfile": cfile,
        "ofile": ofile,
        "working_dir": working_dir,
        "arguments": arguments
    }

def replace_working_dir(cfile, old, new):
    working_dir = cfile["working_dir"]
    assert old in working_dir
    cfile["working_dir"] = working_dir.replace(old, new)

def cfile_exists(cfile):
    path = os.path.join(cfile["working_dir"], cfile["cfile"])
    if os.path.isfile(path):
        return True

    print(f"warning: file not found in redist2017: {path}")

def process_program(program_name, data, use_redist_2017=False):

    processed_cfiles = [process_cfile(cfile) for cfile in data["cfiles"]]

    # Remove None-cfiles, as they have been skipped
    processed_cfiles = [cfile for cfile in processed_cfiles if cfile is not None]

    # Perform redist-specific changes
    if use_redist_2017:
        if program_name == "505.mcf":
            return None

        if program_name == "500.perlbench":
            for cfile in processed_cfiles:
                replace_working_dir(cfile, "cpu2017/benchspec/CPU/500.perlbench_r/src", "redist2017/extracted/500.perlbench/perl-5.22.1")

        # Remove any C files that can no longer be found
        processed_cfiles = [cfile for cfile in processed_cfiles if cfile_exists(cfile)]

    # Sort cfiles
    processed_cfiles.sort(key=lambda x:x["cfile"])

    return {
        **data,
        "cfiles": processed_cfiles
    }


def main():
    parser = argparse.ArgumentParser(description='Process sources-raw.json to clean up paths')

    parser.add_argument('--input', dest='input', action='store', default='sources-raw.json',
                        help="The name of the input json file [sources-raw.json]")
    parser.add_argument('--output', dest='output', action='store', default='sources.json',
                        help="The name of the destination json file [sources.json]")
    parser.add_argument('--useRedist2017', dest='use_redist_2017', action='store_true',
                        help="If set, cpu2017/ paths are replaced by redist2017/ paths")

    args = parser.parse_args()

    with open(args.input, 'r', encoding='utf-8') as input_file:
        programs = json.load(input_file)

    programs = {key: process_program(key, value, args.use_redist_2017) for key, value in programs.items()}

    # Remove programs that have been None-d out
    programs = {key: value for key, value in programs.items() if value is not None}

    with open(args.output, 'w', encoding='utf-8') as output_file:
        json.dump(programs, output_file, indent=2)

if __name__ == "__main__":
    main()
