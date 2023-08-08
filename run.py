import sys
# import subprocess
import pexpect

def run_command(command):
	print("COMMAND START: {}".format(command))
	print("")

	child = pexpect.spawn("/bin/bash", ['-c', command])
	child.logfile = sys.stdout.buffer
	return child

def expect_command_end(child):
	child.expect(pexpect.EOF)
	print("")
	if child.wait() != 0:
		raise RuntimeError("Failed to execute command: '{}'".format(command))

def run_command_simple(command):
	child = run_command(command)
	expect_command_end(child)

# run_command_simple("./test_command \"first command\" 3")

# child = run_command("./test_command \"first command\" 5")
# child.expect("stderr")
# print("hello")
# expect_command_end(child)

# run_command_simple("./test_command \"second command\" 3")
# # TODO proper forwarding of error messages?

# TODO check stdout is written to stdout, stderr is written to stderr?

qemu_process = run_command(
	"./cheribuild/cheribuild.py --source-root cheri run-riscv64-purecap --run-riscv64-purecap/ephemeral " \
	"--run-riscv64-purecap/extra-options=\"--icount shift=0,align=off --cheri-trace-backend drcachesim " \
	"--cheri-trace-drcachesim-tracefile /dev/null --cheri-trace-drcachesim-dbgfile /dev/null\"")

qemu_process.expect("login:", timeout=None)

# qemu_process.sendline("toor")
# qemu_process.sendline("ls")
# qemu_process.wait()

qemu_process.sendcontrol('a')
qemu_process.send('x')
expect_command_end(qemu_process)

