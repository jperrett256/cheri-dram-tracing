#!/usr/bin/env bash
set -ex

if [ "$#" -ne 1 ] || ! [ -f "$1" ]; then
  echo "Usage: $0 <SPEC .iso path>" >&2
  exit 1
fi
spec_path=$1

# snippet taken from: https://stackoverflow.com/a/246128/6887828
script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

########################### build qemu and cheribsd ###########################

$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri qemu --qemu/configure-options="--enable-drcachesim-log-instr"
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri --include-dependencies --only-dependencies run-riscv64-purecap

############################# build SPEC binaries #############################

# NOTE: this will not be visible in qemu until after the disk image is rebuilt (step below)
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri spec2006-riscv64-purecap --spec2006-riscv64-purecap/iso-path $spec_path

############################ generate SPEC scripts ############################

# NOTE: this will not be visible in qemu until after the disk image is rebuilt (step below)
pushd $script_dir/cheri/output/rootfs-riscv64-purecap/opt/
mkdir -p spec2006_scripts
$script_dir/generate_spec_scripts.py spec2006_scripts
popd

########### populate qemu disk image with SPEC binaries and scripts ###########

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
