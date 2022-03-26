import os
import pty
import shlex
import subprocess

import pytest



def test_stdout_stderr():
    example_script = 'demo.py'
    test_command = 'stdout_stderr'
    out, err = run_from_shell(example_script, test_command)
    assert 'stdout' in out
    assert 'stderr' in err


def test_pygrep():
    example_script = 'pygrep.py'

    # The pygrep example includes CSI codes to highlight matches.
    # We'll strip them out to make checking results easier
    def remove_highlight(text):
        _CSI = "\x1B["
        _HL_START = _CSI + "\033[1m\033[91m"
        _HL_END = _CSI + "0m"
        return text.replace(_HL_START, '').replace(_HL_END, '')

    test_command = r'pygrep "^sourcepy\(\)" sourcepy.sh'
    out, err = run_from_shell(example_script, test_command)
    out = remove_highlight(out)
    assert 'sourcepy()' in out
    assert len(err) == 0

    test_command = r'pygrep "^sourcepy\(\)" < sourcepy.sh'
    out, err = run_from_shell(example_script, test_command)
    out = remove_highlight(out)
    assert 'sourcepy()' in out
    assert len(err) == 0

    test_command = r'echo $RANDOM | pygrep "\d" '
    out, err = run_from_shell(example_script, test_command)
    out = remove_highlight(out)
    assert out.isdigit()
    assert len(err) == 0

    test_command = r'pygrep "^sourcepy\(\)" filedoesnotexist'
    out, err = run_from_shell(example_script, test_command)
    assert len(out) == 0
    assert len(err) > 0





# Helpers

def run_from_shell(example_script, test_command):
    """Sets up Sourcepy and sources `example_script`, then runs
    the specified command from the top level directory
    """
    command = f"""\
        bash -c '
            source sourcepy.sh;
            source examples/{example_script};
            {test_command};
        '
    """
    _, child_fd = os.openpty()
    p = subprocess.Popen(shlex.split(command), stdin=child_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out.decode().strip(), err.decode().strip()
