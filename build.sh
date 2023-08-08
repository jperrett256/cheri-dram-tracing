#!/usr/bin/env bash
set -e

if [ "$#" -ne 1 ] || ! [ -f "$1" ]; then
  echo "Usage: $0 <SPEC .iso path>" >&2
  exit 1
fi
spec_path=$1

# snippet taken from: https://stackoverflow.com/a/246128/6887828
script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

########################### build qemu and cheribsd ###########################

$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri qemu --qemu/configure-options="--enable-drcachesim-log-instr"
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri -d run-riscv64-purecap --run-riscv64-purecap/ephemeral \
    --run-riscv64-purecap/extra-options="--icount shift=0,align=off --cheri-trace-backend drcachesim --cheri-trace-drcachesim-tracefile /dev/null --cheri-trace-drcachesim-dbgfile /dev/null"

############# build SPEC binaries and populate qemu image with it #############

$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri spec2006-riscv64-purecap --spec2006-riscv64-purecap/iso-path $spec_path
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri disk-image-riscv64-purecap

#################### build dynamorio (includes drcachesim) ####################

mkdir -p $script_dir/dynamorio_build
pushd $script_dir/dynamorio_build
cmake ../dynamorio
make -j
popd

############################### build traceconv ###############################

pushd $script_dir/cheri-trace-converter
make
popd

############# make fifos for piping trace data between components #############

mkdir -p $script_dir/fifos
mkfifo $script_dir/fifos/fifo_trace_raw
mkfifo $script_dir/fifos/fifo_trace_compressed.lz4
mkfifo $script_dir/fifos/fifo_trace_split_a.lz4
mkfifo $script_dir/fifos/fifo_trace_split_b.lz4
mkfifo $script_dir/fifos/fifo_trace_drcachesim.lz4
