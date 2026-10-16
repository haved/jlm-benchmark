#!/usr/bin/bash
export JLM_DISABLE_IMPLICIT_MODREF_REPRESENTATION=1
export JLM_DISABLE_FUNCTION_SIMPLE_ALLOCA_ALLOWLIST=1
export JLM_DISABLE_CALL_SIMPLE_ALLOCA_ALLOWLIST=1
export JLM_DISABLE_EXTERN_SIMPLE_ALLOCA_ALLOWLIST=1
export JLM_DISABLE_MEMORY_STATE_DISTRIBUTION_STATISTICS=1

./benchmark.py "--jlm-opt=${JLM_PATH:-jlm}/build-release/jlm-opt" --llvmbin=/usr/lib/llvm-18/bin --sources=sources/sources.json -j=1 --full-spec '--filter=5\d\d\.' --filter=emacs --filter=gdb --filter=ghostscript --filter=sendmail --noStrictAliasing --optSroa --pre-jlm-name sroa --regionAwareModRef --jlm-name sroa-raw-omf-cmf-osf-7 --skipTreePrinting --nullOutput