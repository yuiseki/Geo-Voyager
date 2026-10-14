from dataclasses import dataclass
import re
import subprocess

# A diagnostic (stderr, the stdout of a failed run) is shown to a model as it is: 8 KiB.
OUTPUT_LIMIT = 8192
# A result is passed whole to the next step's code (results[...]) and cut to a budget where a prompt shows it
# (goal_history, critic). A table of the 217 countries of the world, or of the 1,741 municipalities of Japan, fits.
RESULT_LIMIT = 256 * 1024
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
    def __init__(self, limit):
        self.limit, self.kept, self.size = limit, [], 0
    def write(self, text):
        data = text.encode('utf-8')
        if self.size < self.limit:
            self.kept.append(data[:self.limit - self.size])
        self.size += len(data)
        return len(text)
    @property
    def text(self):
        return b''.join(self.kept).decode('utf-8', errors='ignore')
    def flush(self):
        pass
original_out, original_err = sys.stdout, sys.stderr
out, err = LimitedOutput(''' + str(RESULT_LIMIT) + '''), LimitedOutput(''' + str(OUTPUT_LIMIT) + ''')
sys.stdout, sys.stderr = out, err
status = 0
try:
    exec(compile(''' + repr(code) + ''', '<candidate>', 'exec'), {'__name__': '__main__'})
except BaseException:
    traceback.print_exc(limit=8)
    status = 73
finally:
    # Output cut at the limit would reach the Critic as a list that stops mid-row. It fails, saying what to change.
    if status == 0 and out.size > out.limit:
        err.write('OutputTooLong: 出力が %d bytes で、上限 %d bytes を超えた。Intent が求める値だけを残し、返す行か列を減らす\\n' % (out.size, out.limit))
        status = 73
    sys.stdout, sys.stderr = original_out, original_err
    for stream, kept in ((original_out, out), (original_err, err)):
        text = kept.text
        for key, value in os.environ.items():
            if len(value) >= 8 or any(word in key.upper() for word in ('TOKEN', 'SECRET', 'PASSWORD', 'KEY')):
                text = text.replace(value, '[redacted]')
        # A failed run's stdout is a diagnostic.
        stream.write(text.encode('utf-8')[:kept.limit if status == 0 else ''' + str(OUTPUT_LIMIT) + '''].decode('utf-8', errors='ignore'))
sys.exit(status)
'''
