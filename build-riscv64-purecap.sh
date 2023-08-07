#!/usr/bin/env bash
set -e

# snippet taken from: https://stackoverflow.com/a/246128/6887828
script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri qemu --qemu/configure-options="--enable-drcachesim-log-instr"
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri -d run-riscv64-purecap --run-riscv64-purecap/ephemeral \
    --run-riscv64-purecap/extra-options="--icount shift=0,align=off --cheri-trace-backend drcachesim --cheri-trace-drcachesim-tracefile /dev/null --cheri-trace-drcachesim-dbgfile /dev/null"
