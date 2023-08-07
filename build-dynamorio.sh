#!/usr/bin/env bash
set -e

# snippet taken from: https://stackoverflow.com/a/246128/6887828
script_dir=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p $script_dir/dynamorio_build
pushd $script_dir/dynamorio_build
cmake ../dynamorio
make -j
popd
