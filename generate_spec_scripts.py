#!/usr/bin/env python3

import spec_commands as SPEC
import os
import os.path
import argparse

def write_benchmark_script(output_dir, output_name, benchmark_variant):
	output_path = os.path.join(output_dir, output_name)
	# NOTE using an opener of os.open with a umask of 022 yields execute permissions on the generated files
	with open(output_path, "w", opener=os.open) as output_file:
		output_file.write("#!/bin/sh\n")
		output_file.write("set -ex\n")
		for command in benchmark_variant.setup + benchmark_variant.execution:
			output_file.write(f"{command}\n")

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description="Generates SPEC2006 benchmark scripts for running within cheribsd.")
	parser.add_argument("output_dir", type=str, metavar="path", help="Output directory path")
	args = parser.parse_args()

	if not os.path.isdir(args.output_dir):
		raise RuntimeError(f"Output directory path not valid: '{args.output_dir}'")

	os.umask(0o022) # NOTE this is likely the default already, but setting to be sure
	for benchmark_name in SPEC.all_benchmarks:
		benchmark = SPEC.all_benchmarks[benchmark_name]
		write_benchmark_script(args.output_dir, f"{benchmark_name}.test.sh", benchmark.test)
		write_benchmark_script(args.output_dir, f"{benchmark_name}.train.sh", benchmark.train)
		write_benchmark_script(args.output_dir, f"{benchmark_name}.ref.sh", benchmark.ref)
