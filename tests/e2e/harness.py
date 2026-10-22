"""Runs the real ./cli against a disposable checkout and home directory.

Every test gets a sandbox under the repository's ignored .scratch/e2e: a copy of
the CLI, an empty home, and doubles for the external commands it runs (see
boundary.py). The environment is built from an allowlist, so a variable from the
developer's session, such as CODEX_HOME or CLAUDE_CONFIG_DIR, can never point
the CLI at real configuration. Node, git, bash and the user's login shell are
real; git cannot discover the enclosing checkout.
"""
import atexit
import fcntl
import json
import os
import plistlib
import pty
import select
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOUNDARY = Path(__file__).resolve().parent / 'boundary.py'
COMMANDS = ['brew', 'curl', 'gh', 'yay', 'pacman', 'systemctl', 'launchctl', 'mise', 'npx',
            'omarchy-pkg-present', 'omarchy-pkg-add', 'omarchy-pkg-aur-add', 'omarchy-install-gaming-steam',
            'omarchy-install-service-tailscale', 'omarchy-install-editor-zed', 'omarchy-install-browser']
EMPTY_STATE = {
    'unexpected': [],
    'brew': {'formulae': [], 'casks': [], 'taps': []},
    'gh': {'extensions': []},
    'pacman': {'installed': [], 'aur': [], 'broken': False},
    'systemd': {'loaded': [], 'active': [], 'results': {}},
    'launchd': {'loaded': {}, 'exits': {}, 'env': {}},
    'mise': {'ls': {}, 'doctor': 0, 'settings': {}, 'pruned': 0},
    'npx': {'status': None, 'calls': []},
    'vp': {'mode': 'managed'},
    't3code': {'tags': [], 'manifests': {}, 'downloads': []},
}


def _remove(path):
    # A test may leave a directory unreadable on purpose.
    def unlock(function, name, _):
        os.chmod(os.path.dirname(name), 0o755)
        os.chmod(name, 0o755)
        function(name)
    shutil.rmtree(path, onexc=unlock)


(ROOT / '.scratch/e2e').mkdir(parents=True, exist_ok=True)
RUN = Path(tempfile.mkdtemp(prefix='', dir=ROOT / '.scratch/e2e'))
atexit.register(_remove, RUN)
# tsx listens on a Unix socket under TMPDIR, and socket paths are limited to 104 bytes on macOS.
if len(str(RUN / 'tmp/tsx-0000/0000000.pipe')) > 103:
    raise RuntimeError(f'{RUN} is too deep for tsx\'s socket; run the tests from a checkout with a shorter path')
TOOLS = RUN / 'tools'
TOOLS.mkdir()
# The real node binary, not a version manager's shim: a Vite+ shim puts its own
# runtime directory first on its children's PATH, ahead of the doubles.
_node = shutil.which('node')
if _node is None:
    raise RuntimeError('the e2e tests need node on PATH')
(TOOLS / 'node').symlink_to(subprocess.run([_node, '-p', 'process.execPath'], capture_output=True, text=True, check=True,
                                           env={'PATH': os.environ['PATH'], 'HOME': os.environ.get('HOME', '')}).stdout.strip())
(RUN / 'tmp').mkdir()


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self.sandbox = Path(tempfile.mkdtemp(dir=RUN))
        self.addCleanup(_remove, self.sandbox)
        self.repo, self.home, self.bin = self.sandbox / 'repo', self.sandbox / 'home', self.sandbox / 'bin'
        for directory in [self.repo, self.home, self.bin]:
            directory.mkdir()
        shutil.copy(ROOT / 'cli', self.repo / 'cli')
        shutil.copy(ROOT / 'package.json', self.repo / 'package.json')
        shutil.copy(ROOT / 'tsconfig.json', self.repo / 'tsconfig.json')
        shutil.copytree(ROOT / 'scripts', self.repo / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
        # The mise component's daily launchd job runs this helper from the checkout.
        (self.repo / 'macos/bin').mkdir(parents=True)
        shutil.copy2(ROOT / 'macos/bin/xcode-node-env', self.repo / 'macos/bin/xcode-node-env')
        (self.repo / 'node_modules').symlink_to(ROOT / 'node_modules', target_is_directory=True)
        self.write('macos/agents/CONTEXT.md', 'MAC_CONTEXT')
        self.write('linux/agents/CONTEXT.md', 'LINUX_CONTEXT')
        self.write('shared/skills/personal/unslop/SKILL.md', '---\nname: unslop\n---\n\n# Unslop\n\nUNSLOP_RULES\n')
        self.state_file = self.sandbox / 'boundary.json'
        self.state_file.write_text(json.dumps(EMPTY_STATE))
        for command in COMMANDS:
            self.double(self.bin / command, command)
        self.env = {
            'HOME': str(self.home), 'PATH': os.pathsep.join([str(self.bin), str(TOOLS), '/usr/bin', '/bin', '/usr/sbin', '/sbin']),
            'TMPDIR': str(RUN / 'tmp'), 'USER': os.environ.get('USER', 'tester'), 'LOGNAME': os.environ.get('LOGNAME', 'tester'),
            'LANG': os.environ.get('LANG', 'C.UTF-8'), 'TERM': os.environ.get('TERM', 'xterm-256color'),
            'GIT_CEILING_DIRECTORIES': str(RUN), 'GIT_CONFIG_NOSYSTEM': '1', 'DONNES_CONFIGS_PROFILE': 'macos',
        }
        self.addCleanup(lambda: self.assertEqual(self.state['unexpected'], [], 'the CLI ran a command no double models'))

    def double(self, file, command):
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(f'#!/bin/sh\nexec "{sys.executable}" -I "{BOUNDARY}" "{self.state_file}" {command} "$@"\n')
        file.chmod(0o755)

    @property
    def state(self):
        return json.loads(self.state_file.read_text())

    def boundary(self, **sections):
        """Sets part of the external tools' state, such as installed packages."""
        state = self.state
        for section, values in sections.items():
            state[section].update(values)
        self.state_file.write_text(json.dumps(state))

    def write(self, relative, content, home=False):
        file = (self.home if home else self.repo) / relative
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(content)
        return file

    def cli(self, *args, code=0):
        result = subprocess.run(['bash', str(self.repo / 'cli'), *args], env=self.env, capture_output=True, text=True,
                                stdin=subprocess.DEVNULL, timeout=180)
        if code is not None:
            self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        return result

    def fails(self, *args):
        result = self.cli(*args, code=None)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.com', *args],
                              env=self.env, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self, message='initial'):
        if not (self.repo / '.git').exists():
            self.git('init', '-q')
        self.git('add', '-A')
        self.git('commit', '-qm', message, '--allow-empty')
        return self.git('rev-parse', 'HEAD')

    def opencode(self, version):
        binary = self.write('.opencode/bin/opencode', f'#!/bin/sh\necho opencode v{version}\n', home=True)
        binary.chmod(0o755)
        return binary

    def launchd_job(self, label):
        """Runs a loaded launchd agent's program as launchd would, recording its exit code.
        Only the absolute boundary executables in it are swapped for doubles."""
        plist = plistlib.loads(Path(self.state['launchd']['loaded'][label]).read_bytes())
        self.assertEqual(plist['ProgramArguments'][:2], ['/bin/sh', '-c'])
        script = plist['ProgramArguments'][2]
        swapped = script.replace('/bin/launchctl ', f'"{self.bin}/launchctl" ').replace('export PATH="', f'export PATH="{self.bin}:', 1)
        self.assertNotEqual(swapped, script, f'{label} runs no known boundary executable')
        # launchd starts jobs with a minimal environment of its own.
        result = subprocess.run(['/bin/sh', '-c', swapped], env={'HOME': str(self.home), 'PATH': '/usr/bin:/bin:/usr/sbin:/sbin'},
                                capture_output=True, text=True, timeout=60)
        state = self.state
        state['launchd']['exits'][label] = result.returncode
        self.state_file.write_text(json.dumps(state))
        return result

    def interactive(self, args, exchanges, code=0, piped=False):
        """Drives the CLI in a pseudo-terminal: waits for each prompt text, then types its reply."""
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 100, 0, 0))

        def terminal_session():
            os.setsid()
            fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        command = (['bash', '-c', 'cat "$1" | bash -s -- "${@:2}"', 'bootstrap', str(self.repo / 'cli'), *args]
                   if piped else ['bash', str(self.repo / 'cli'), *args])
        process = subprocess.Popen(command, env=self.env, stdin=slave, stdout=slave, stderr=slave,
                                   preexec_fn=terminal_session)
        os.close(slave)
        output = b''

        def read():
            nonlocal output
            if select.select([master], [], [], 0.1)[0]:
                try:
                    chunk = os.read(master, 65536)
                except OSError:
                    chunk = b''
                output += chunk
                return bool(chunk)
            return True
        try:
            for expected, reply in exchanges:
                deadline = time.monotonic() + 20
                while expected.encode() not in output:
                    if time.monotonic() > deadline:
                        raise AssertionError(f'Timed out waiting for {expected!r}: {output.decode(errors="replace")}')
                    if not read():
                        raise AssertionError(f'CLI exited before {expected!r}: {output.decode(errors="replace")}')
                os.write(master, reply.encode())
            deadline = time.monotonic() + 20
            while process.poll() is None:
                if time.monotonic() > deadline:
                    raise AssertionError(f'CLI did not exit: {output.decode(errors="replace")}')
                if not read():
                    break
            process.wait(timeout=5)
            self.assertEqual(process.returncode, code, output.decode(errors='replace'))
            return output.decode(errors='replace')
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            os.close(master)

    def health(self, code, *args):
        """Runs ./cli health --json and returns its report."""
        result = self.cli('health', '--json', *args, code=code)
        return json.loads(result.stdout)

    def check(self, report, status, section, *words):
        """Asserts that a check in `section` mentioning every word has `status`, and returns it."""
        matches = [check for check in report['checks'] if check['section'].startswith(section)
                   and all(word in check['message'] for word in words)]
        self.assertTrue(matches, f'no {section} check mentions {words}: {json.dumps(report["checks"], indent=1)}')
        self.assertIn(status, [check['status'] for check in matches], json.dumps(matches, indent=1))
        return matches

    def warnings(self, report):
        return sorted(check.get('id', check['message']) for check in report['checks'] if check['status'] == 'warn')

    def failures(self, report):
        return [f'{check["section"]}: {check["message"]}' for check in report['checks'] if check['status'] == 'fail']

