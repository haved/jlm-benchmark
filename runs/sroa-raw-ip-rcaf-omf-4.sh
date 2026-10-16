#!/usr/bin/bash
export JLM_DISABLE_CONSTANT_MEMORY_BLOCKING=1
export JLM_DISABLE_READ_ONLY_DETECTION=1
export JLM_DISABLE_OPERATION_SIZE_BLOCKING=1
export JLM_DISABLE_MEMORY_STATE_DISTRIBUTION_STATISTICS=1

./benchmark.py "--jlm-opt=${JLM_PATH:-jlm}/build-release/jlm-opt" --llvmbin=/usr/lib/llvm-18/bin --sources=sources/sources.json -j=1 --full-spec '--filter=5\d\d\.' --filter=emacs --filter=gdb --filter=ghostscript --filter=sendmail --noStrictAliasing --optSroa --pre-jlm-name sroa --regionAwareModRef --jlm-name sroa-raw-ip-rcaf-omf-4 --skipTreePrinting --nullOutput