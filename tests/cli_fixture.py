"""Run the public CLI against a disposable checkout and home directory."""
import os
import fcntl
from pathlib import Path
import pty
import select
import signal
import shutil
import subprocess
import struct
import termios
import time

ROOT = Path(__file__).resolve().parents[1]


def copy_cli(repo):
    shutil.copy(ROOT / 'cli', repo / 'cli')
    shutil.copy(ROOT / 'package.json', repo / 'package.json')
    shutil.copytree(ROOT / 'scripts', repo / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
    (repo / 'node_modules').symlink_to(ROOT / 'node_modules', target_is_directory=True)


def interactive_cli(repo, env, args, exchanges, expected_code=0, piped=False):
    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))
    def terminal_session():
        os.setsid()
        fcntl.ioctl(0, termios.TIOCSCTTY, 0)
    command = (['bash', '-c', 'cat "$1" | bash -s -- "${@:2}"', 'bootstrap', str(repo / 'cli'), *args]
               if piped else ['bash', str(repo / 'cli'), *args])
    process = subprocess.Popen(command, env=env, stdin=slave, stdout=slave, stderr=slave,
                               preexec_fn=terminal_session)
    os.close(slave)
    output = b''
    try:
        for expected, reply in exchanges:
            deadline = time.monotonic() + 10
            while expected.encode() not in output:
                if time.monotonic() > deadline:
                    raise AssertionError(f'Timed out waiting for {expected!r}: {output.decode(errors="replace")}')
                if select.select([master], [], [], 0.1)[0]:
                    try:
                        chunk = os.read(master, 65536)
                    except OSError:
                        chunk = b''
                    if not chunk:
                        raise AssertionError(f'CLI exited before {expected!r}: {output.decode(errors="replace")}')
                    output += chunk
            os.write(master, reply.encode())
        deadline = time.monotonic() + 10
        while process.poll() is None:
            if time.monotonic() > deadline:
                raise AssertionError(f'CLI did not exit: {output.decode(errors="replace")}')
            if select.select([master], [], [], 0.1)[0]:
                try:
                    output += os.read(master, 65536)
                except OSError:
                    break
        process.wait(timeout=5)
        if process.returncode != expected_code:
            raise AssertionError(f'Expected exit {expected_code}, got {process.returncode}: '
                                 + output.decode(errors='replace'))
        return output.decode(errors='replace')
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        os.close(master)
