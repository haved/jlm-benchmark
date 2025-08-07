#!/usr/bin/env python3

import argparse
import json
import re
import os

# If true, paths inside cpu2017/ are replaced by paths in redist2017/
use_redist_2017 = False

# Arguments that should be removed
IGNORED_ARGUMENTS = [
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
    if any(cfile.endswith(s) for s in SKIPPED_FILES):
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


def process_program(name, data):
    processed_cfiles = [process_cfile(cfile) for cfile in data["cfiles"]]

    # Remove None-cfiles, as they have been skipped
    processed_cfiles = [cfile for cfile in processed_cfiles if cfile is not None]

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
    parser.add_argument('--check', dest='check', action='store_true',
                        help="Check that all C files exist")

    args = parser.parse_args()
    global use_redist_2017
    use_redist_2017 = args.use_redist_2017

    with open(args.input, 'r', encoding='utf-8') as input_file:
        programs = json.load(input_file)

    programs = {key: process_program(key, value) for key, value in programs.items()}

    missing_cfiles = []
    if args.check:
        for program in programs.values():
            for cfile_data in program["cfiles"]:
                working_dir = cfile_data["working_dir"]
                cfile = cfile_data["cfile"]
                path = os.path.join(working_dir, cfile)
                if not os.path.isfile(path):
                    missing_cfiles.append(path)
    if missing_cfiles:
        print("Cfile(s) missing!!!")
        for cfile in missing_cfiles:
            print(cfile)
        sys.exit(1)


    with open(args.output, 'w', encoding='utf-8') as output_file:
        json.dump(programs, output_file, indent=2)

if __name__ == "__main__":
    main()
