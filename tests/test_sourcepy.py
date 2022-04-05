import os
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


def test_variables():
    example_script = 'demo.py'

    test_command = 'echo $MY_INT; MY_INT=6*7; echo $MY_INT'
    out, err = run_from_shell(example_script, test_command)
    print(out, err)
    assert '21' in out
    assert '42' in out
    assert len(err) == 0

    test_command = 'echo "My favourite drummer is ${FAB_FOUR[-1]}"'
    out, err = run_from_shell(example_script, test_command)
    assert 'My favourite drummer is Ringo' in out
    assert len(err) == 0

    test_command = 'echo "This is ${PROJECT[name]} and its primary purpose is ${PROJECT[purpose]}"'
    out, err = run_from_shell(example_script, test_command)
    assert 'This is Sourcepy and its primary purpose is unknown' in out
    assert len(err) == 0


def test_help():
    example_script = 'demo.py'

    test_command = 'multiply --help'
    out, err = run_from_shell(example_script, test_command)
    assert "usage: multiply [-h] [-x int] [-y int]" in err
    assert "positional or keyword args" in err
    assert "x (-x, --x)" in err
    assert "int (required)" in err
    assert len(out) == 0

    test_command = 'pretzel.do -h'
    out, err = run_from_shell(example_script, test_command)
    assert "usage: pretzel.do [-h] [-a {'sit', 'speak', 'drop'}]" in err
    assert "action (-a, --action)" in err
    assert "{'sit', 'speak', 'drop'} (default: None)" in err
    assert len(out) == 0

    test_command = 'favouritecolour --help'
    out, err = run_from_shell(example_script, test_command)
    assert "usage: favouritecolour [-h] [-c {'RED', 'GREEN', 'BLUE'}]" in err
    assert "colour (-c, --colour)" in err
    assert "{'RED', 'GREEN', 'BLUE'} (required)" in err
    assert len(out) == 0

    example_script = 'pygrep.py'

    test_command = 'pygrep --help'
    out, err = run_from_shell(example_script, test_command)
    assert "usage: pygrep [-h] [-p Pattern] [-g [file/stdin ...]]" in err
    assert "[file/stdin ...] (required)" in err
    assert len(out) == 0


def test_errors():
    example_script = 'demo.py'

    test_command = 'multiply a b'
    out, err = run_from_shell(example_script, test_command)
    assert "multiply: error: argument x: invalid int value: 'a'" in err
    assert len(out) == 0

    test_command = 'pretzel.do fly'
    out, err = run_from_shell(example_script, test_command)
    assert "pretzel.do: error: argument action: invalid choice: 'fly' (choose from 'sit', 'speak', 'drop')" in err
    assert len(out) == 0

    test_command = 'favouritecolour -c YELLOW'
    out, err = run_from_shell(example_script, test_command)
    assert "favouritecolour: error: argument colour: invalid choice: 'YELLOW' (choose from 'RED', 'GREEN', 'BLUE')" in err
    assert len(out) == 0

    example_script = 'pygrep.py'

    test_command = 'pygrep "test" thisfiledoesnotexist'
    out, err = run_from_shell(example_script, test_command)
    assert "pygrep: error: argument grepdata: no such file or directory: thisfiledoesnotexist" in err
    assert len(out) == 0



def test_asyncio():
    example_script = 'asynciodemo.py'

    test_command = 'say_after 1 test123'
    out, err = run_from_shell(example_script, test_command)
    assert "test123" in err
    assert len(out) == 0 # the asyncio only prints and returns nothing, so stdout will always be blank

    test_command = 'main'
    out, err = run_from_shell(example_script, test_command)
    assert "started at" in err
    assert "hello" in err
    assert "world" in err
    assert "finished at" in err
    assert len(out) == 0

    test_command = 'say_after -h'
    out, err = run_from_shell(example_script, test_command)
    assert "say_after [-h] [-d] [-w]" in err
    assert "delay (-d, --delay)" in err
    assert "what (-w, --what)" in err
    assert len(out) == 0



# Helpers

def run_from_shell(example_script, test_command):
    """Sets up Sourcepy and sources `example_script`, then runs
    the specified command from the top level directory
    """
    shell = os.environ.get('SHELL', 'bash')
    command = f"""\
        {shell} -c '
            source sourcepy.sh;
            source examples/{example_script};
            {test_command};
        '
    """
    _, child_fd = os.openpty()
    with subprocess.Popen(shlex.split(command), stdin=child_fd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p:
        out, err = p.communicate()
    return out.decode().strip(), err.decode().strip()
