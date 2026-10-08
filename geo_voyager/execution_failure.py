from dataclasses import dataclass
import re
import subprocess

OUTPUT_LIMIT = 8192
GENERATED_ERROR_EXIT = 73


def bounded_output(text: str | bytes | None) -> str:
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='replace')
    lines = (text or '').splitlines()
    safe = [line if not re.search(r'(?i)(token|password|secret|api[_-]?key|authorization|environ)', line)
            else '[redacted]' for line in lines]
    return '\n'.join(safe)[:OUTPUT_LIMIT]


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
        self.text += text[:max(0, 8192 - len(self.text))]
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
            if len(value) >= 8:
                text = text.replace(value, '[redacted]')
        stream.write(text)
sys.exit(status)
'''
