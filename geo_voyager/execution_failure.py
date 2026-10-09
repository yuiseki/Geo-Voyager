from dataclasses import dataclass
import re
import subprocess

OUTPUT_LIMIT = 8192
GENERATED_ERROR_EXIT = 73


def bounded_output(text: str | bytes | None) -> str:
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    lines = (text or '').splitlines()
    sensitive = re.compile(r"""\b(?:(?i:token|password|secret|api[_-]?key|authorization)|HOME|PATH|HOSTNAME|PWD)['"]?\s*[:=]|\benviron\b""")
    safe = [line if not sensitive.search(line) else '[redacted]' for line in lines]
    return '\n'.join(safe).encode('utf-8')[:OUTPUT_LIMIT].decode('utf-8', errors='ignore')


_CANDIDATE_FRAME = re.compile(r'(File "<candidate>", line )(\d+)')


def candidate_lines(stderr: str, offset: int) -> str:
    """Number the <candidate> frames of a traceback by the candidate's own code.

    The Worker puts `offset` lines of runtime variables in front of the code it runs, so Python
    counts that many lines more than the code the Generator or the Repairer wrote. A frame at or
    before the injected lines is left as it is.
    """
    if offset <= 0:
        return stderr

    def shift(match):
        line = int(match.group(2))
        return match.group(1) + str(line - offset if line > offset else line)
    return _CANDIDATE_FRAME.sub(shift, stderr)


@dataclass(frozen=True)
class ExecutionFailure:
    message: str
    stdout: str
    stderr: str
    exit_code: int | None

    @classmethod
    def from_process(cls, error: subprocess.CalledProcessError) -> 'ExecutionFailure':
        return cls('Generated Python execution failed', bounded_output(error.stdout),
                   bounded_output(error.stderr), error.returncode)


def sandbox_program(code: str) -> str:
    # The wrapper runs inside the container. No host environment is copied.
    return '''import io, os, sys, traceback
class LimitedOutput(io.TextIOBase):
    def __init__(self):
        self.text = ''
    def write(self, text):
        self.text += text.encode('utf-8')[:max(0, 8192 - len(self.text.encode('utf-8')))].decode('utf-8', errors='ignore')
        return len(text)
    def flush(self):
        pass
original_out, original_err = sys.stdout, sys.stderr
out, err = LimitedOutput(), LimitedOutput()
sys.stdout, sys.stderr = out, err
status = 0
try:
    exec(compile(''' + repr(code) + ''', '<candidate>', 'exec'), {'__name__': '__main__'})
except BaseException:
    traceback.print_exc(limit=8)
    status = 73
finally:
    sys.stdout, sys.stderr = original_out, original_err
    for stream, text in ((original_out, out.text), (original_err, err.text)):
        for key, value in os.environ.items():
            if len(value) >= 8 or any(word in key.upper() for word in ('TOKEN', 'SECRET', 'PASSWORD', 'KEY')):
                text = text.replace(value, '[redacted]')
        stream.write(text.encode('utf-8')[:8192].decode('utf-8', errors='ignore'))
sys.exit(status)
'''
