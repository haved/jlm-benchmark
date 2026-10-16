#!/usr/bin/env python3

"""
This script creates separate .sh files for all configurations and iterations
"""

import shutil
from pathlib import Path

DEST_FOLDER = Path("runs/")
NUM_PER_CONFIG = 10

# By default disable everything
# The del keyword throws an error if we try to delete a missing key
DEFAULT_ENV = {
    "JLM_DISABLE_IMPLICIT_MODREF_REPRESENTATION": 1,

    "JLM_DISABLE_OMEGA_FOLDING": 1,

    "JLM_DISABLE_FUNCTION_SIMPLE_ALLOCA_ALLOWLIST": 1,
    "JLM_DISABLE_CALL_SIMPLE_ALLOCA_ALLOWLIST": 1,
    "JLM_DISABLE_EXTERN_SIMPLE_ALLOCA_ALLOWLIST": 1,

    "JLM_DISABLE_CONSTANT_MEMORY_BLOCKING": 1,
    "JLM_DISABLE_READ_ONLY_DETECTION": 1,

    "JLM_DISABLE_OPERATION_SIZE_BLOCKING": 1,
}

def createScript(name, flags, env, number):
    name_and_number = f"{name}-{number}"
    path = DEST_FOLDER / f"{name_and_number}.sh"

    with open(path, 'w', encoding='utf-8') as fd:
        fd.write("#!/usr/bin/bash\n")

        for key, value in env.items():
            fd.write(f"export {key}={value}\n")

        # Avoid dumping full statistics for every iteration
        if number > 0:
            fd.write("export JLM_DISABLE_MEMORY_STATE_DISTRIBUTION_STATISTICS=1\n")

        fd.write("\n")
        fd.write("./benchmark.py ")
        fd.write('"--jlm-opt=${JLM_PATH:-jlm}/build-release/jlm-opt" ')
        fd.write("--llvmbin=/usr/lib/llvm-18/bin --sources=sources/sources.json -j=1 ")
        fd.write("--full-spec '--filter=5\\d\\d\\.' --filter=emacs --filter=gdb --filter=ghostscript --filter=sendmail ")
        fd.write("--noStrictAliasing ")
        fd.write(" ".join(flags) + " ")
        fd.write(f"--jlm-name {name_and_number} ")

        # Avoid tree printing and storing output files for every iteration
        if number > 0:
            fd.write("--skipTreePrinting --nullOutput")

def createScripts(optPipeline, modRefType, enableRcaf, enableOmegaFolding, enableCmf, enableOsf):
    name = []
    env = DEFAULT_ENV.copy()
    flags = []

    if optPipeline == "sroa":
        flags.extend(["--optSroa", "--pre-jlm-name", "sroa"])
    else:
        raise ValueError("Other opt pipelines not defined")
    name.append(optPipeline)

    if modRefType == "raw":
        flags.append("--regionAwareModRef")
    elif modRefType == "raw-ip":
        flags.append("--regionAwareModRef")
        del env["JLM_DISABLE_IMPLICIT_MODREF_REPRESENTATION"]
    elif modRefType == "rag":
        flags.append("--agnosticModRef")
    else:
        raise ValueError(f"Unknown modRefType: {modRefType}")
    name.append(modRefType)

    if enableRcaf:
        del env["JLM_DISABLE_FUNCTION_SIMPLE_ALLOCA_ALLOWLIST"]
        del env["JLM_DISABLE_CALL_SIMPLE_ALLOCA_ALLOWLIST"]
        del env["JLM_DISABLE_EXTERN_SIMPLE_ALLOCA_ALLOWLIST"]
        name.append("rcaf")
        # Register confined allocas only exist in the region aware summarizer
        assert "raw" in modRefType

    if enableOmegaFolding:
        del env["JLM_DISABLE_OMEGA_FOLDING"]
        name.append("omf")
        assert "raw" in modRefType or "rag" in modRefType

    if enableCmf:
        del env["JLM_DISABLE_CONSTANT_MEMORY_BLOCKING"]
        del env["JLM_DISABLE_READ_ONLY_DETECTION"]
        name.append("cmf")
        assert "raw" in modRefType or "rag" in modRefType

    if enableOsf:
        del env["JLM_DISABLE_OPERATION_SIZE_BLOCKING"]
        name.append("osf")
        assert "raw" in modRefType or "rag" in modRefType

    name_string = "-".join(name)
    for i in range(NUM_PER_CONFIG):
        createScript(name_string, flags, env, i)

def pickOsf(**kwargs):
    createScripts(enableOsf=True, **kwargs)
    createScripts(enableOsf=False, **kwargs)

def pickCmf(**kwargs):
    pickOsf(enableCmf=True, **kwargs)
    pickOsf(enableCmf=False, **kwargs)

def pickOmegaFolding(**kwargs):
    pickCmf(enableOmegaFolding=True, **kwargs)
    pickCmf(enableOmegaFolding=False, **kwargs)

def pickRcaf(**kwargs):
    pickOmegaFolding(enableRcaf=True, **kwargs)
    pickOmegaFolding(enableRcaf=False, **kwargs)

def pickModRefType(**kwargs):
    # Rcaf is always false for rag
    pickOmegaFolding(modRefType="rag", enableRcaf=False, **kwargs)

    pickRcaf(modRefType="raw", **kwargs)
    pickRcaf(modRefType="raw-ip", **kwargs)

def pickOptPipeline(**kwargs):
    pickModRefType(optPipeline="sroa")

def main():
    if DEST_FOLDER.exists():
        shutil.rmtree(DEST_FOLDER)
    DEST_FOLDER.mkdir()

    pickOptPipeline()


if __name__ == "__main__":
    main()
