#!/usr/bin/env bash
set -e

if [ "$#" -ne 1 ] || ! [ -f "$1" ]; then
  echo "Usage: $0 <SPEC .iso path>" >&2
  exit 1
fi
spec_path=$1

# snippet taken from: https://stackoverflow.com/a/246128/6887828
script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri spec2006-riscv64-purecap --spec2006-riscv64-purecap/iso-path $spec_path
$script_dir/cheribuild/cheribuild.py --source-root $script_dir/cheri disk-image-riscv64-purecap
