"""A candidate: the code the Generator (or a repair) wrote for one Intent, before it is known to work.

The code is a short program. It may call saved Skills by name (they are linked in front of it when it runs), and it
may define one new function: the new Skill, which is saved when the Critic accepts the run. The program's top-level
lines pass the runtime values (intent_target, previous_observations, dataset_id, intent_text) to the functions as
arguments; a function that reads them directly would only work for this one Intent.
"""
import ast
from dataclasses import dataclass
import re

from .skill_function import parse_skill

TRIPLE_QUOTE = '"' * 3
RUNTIME_NAMES = ('intent_target', 'previous_observations', 'dataset_id', 'intent_text')


@dataclass(frozen=True)
class SkillCandidate:
    code: str
    description: str
    # The function to call when the code no longer defines it (its copy of a saved Skill was dropped).
    entry: str | None = None


def _main_function(tree: ast.Module) -> ast.FunctionDef | None:
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
    return functions[-1] if functions else None


def main_function_name(code: str) -> str | None:
    try:
        main = _main_function(ast.parse(code))
    except SyntaxError:
        return None
    return main.name if main is not None else None


def _only_imports_and_functions(tree: ast.Module) -> bool:
    return all(isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)) for node in tree.body)


def entry_program(code: str, entry: str | None = None) -> str:
    """The program the sandbox runs: the code, then a call of its main function (the last one) with the runtime
    values its parameters name, and the result printed as JSON. As in Voyager, the model writes only functions and
    the environment calls the main one. Code with statements of its own at the top level is run as it is."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    if not _only_imports_and_functions(tree):
        return code
    main = _main_function(tree)
    if main is None and entry is None:
        return code
    if main is None:
        # The copy of a saved Skill was dropped, and the saved one is linked in front: pass it the runtime values
        # it takes, as found from its signature when it runs.
        return (code.rstrip() + '\n\n\nimport inspect as _inspect\nimport json as _json\n'
                + f'_runtime = {{name: globals().get(name) for name in {RUNTIME_NAMES!r}}}\n'
                + f'_taken = _inspect.signature({entry}).parameters\n'
                + f'print(_json.dumps({entry}(**{{k: v for k, v in _runtime.items() if k in _taken}}), ensure_ascii=False, default=str))')
    names = [a.arg for a in (*main.args.posonlyargs, *main.args.args, *main.args.kwonlyargs)]
    # a runtime value the Intent does not have (no dataset, no target) is passed as None
    arguments = ', '.join(f'{n}=globals().get({n!r})' for n in names if n in RUNTIME_NAMES)
    return (code.rstrip() + '\n\n\n' + 'import json as _json\n'
            + f'print(_json.dumps({main.name}({arguments}), ensure_ascii=False, default=str))')


def entry_problems(code: str) -> list[str]:
    """Why the environment can not call the code's main function: no function, statements at the top level, or a
    parameter that is neither a runtime value nor given a default."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []           # the run reports it
    main = _main_function(tree)
    if main is None:
        return ['関数が無い: 処理を、名前と引数と docstring を持つ関数にまとめる。実行環境がその関数を呼ぶ']
    problems = []
    if not _only_imports_and_functions(tree):
        problems.append('トップレベルに import と関数の定義以外を書いている。実行環境が最後の関数を呼び、戻り値を出力するので、呼び出しや print をトップレベルに書かない')
    positional = [*main.args.posonlyargs, *main.args.args]
    defaults = len(main.args.defaults)
    required = [a.arg for a in positional[:len(positional) - defaults]]
    required += [a.arg for a, d in zip(main.args.kwonlyargs, main.args.kw_defaults) if d is None]
    missing = [name for name in required if name not in RUNTIME_NAMES]
    if missing:
        problems.append(f'関数 {main.name} の引数 {", ".join(missing)} は実行環境から渡せない。'
                        f'実行環境が渡せるのは {", ".join(RUNTIME_NAMES)} だけなので、他の引数には既定値を付ける')
    return problems


def _functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]


def new_skill_code(code: str, description: str = '') -> str | None:
    """The new Skill in a candidate: its imports and its one function. None when it defines no function.

    A local model often leaves out the docstring. The candidate's own description (its 説明) then becomes it.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    functions = _functions(tree)
    if len(functions) != 1:
        return None
    imports = [ast.get_source_segment(code, node) for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    function = functions[0]
    source = ast.get_source_segment(code, function)
    if ast.get_docstring(function) is None and description.strip():
        lines = source.splitlines()
        header = function.body[0].lineno - function.lineno          # the lines of the signature
        indent = ' ' * function.body[0].col_offset
        text = ' '.join(description.split()).replace(TRIPLE_QUOTE, "'''")
        source = '\n'.join(lines[:header] + [indent + TRIPLE_QUOTE + text + TRIPLE_QUOTE] + lines[header:])
    return '\n'.join(imports) + ('\n\n\n' if imports else '') + source


def _returns_a_value(function: ast.FunctionDef) -> bool:
    """A return with a value in the function itself, not in a function nested in it."""
    stack = list(function.body)
    while stack:
        node = stack.pop()
        if isinstance(node, ast.Return) and node.value is not None:
            return True
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)):
            stack.extend(ast.iter_child_nodes(node))
    return False


def skill_shape_problems(code: str, shown: tuple[str, ...] = ()) -> list[str]:
    """Why the candidate does not yield a reusable Skill: no function and no call to a shown Skill, more than one
    function, no docstring, no returned value, or a function that reads a runtime value instead of taking it as an
    argument. Empty when there is nothing wrong. Like Voyager, every run either reuses a Skill or writes one."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []           # the run reports it
    functions = _functions(tree)
    if len(functions) > 1:
        return [f'more than one function: {", ".join(f.name for f in functions)}']
    if not functions:
        called = {node.func.id for node in ast.walk(tree) if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        if called & set(shown):
            return []
        return ['関数が無い: 処理を名前と引数と docstring を持つ関数 1 つにまとめるか、見せた Skill を呼ぶ']
    try:
        parse_skill(new_skill_code(code, description='(the candidate description)') or '')
    except ValueError as error:
        return [str(error)]
    function = functions[0]
    if not _returns_a_value(function):
        return [f'the function {function.name} does not return its result; return it and print it where it is called']
    parameters = {a.arg for a in (*function.args.posonlyargs, *function.args.args, *function.args.kwonlyargs)}
    read = sorted({node.id for node in ast.walk(function) if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                   and node.id in RUNTIME_NAMES and node.id not in parameters})
    return [f'the function {function.name} reads {name} directly; take it as an argument' for name in read]


def _same_function(a: ast.FunctionDef, b: ast.FunctionDef) -> bool:
    """The same name, arguments and body, apart from comments, blank lines and the docstring."""
    def body(function):
        nodes = function.body[1:] if ast.get_docstring(function) is not None else function.body
        nodes = [node for node in nodes if not isinstance(node, (ast.Import, ast.ImportFrom))]   # imports moved in
        return [ast.dump(node) for node in nodes], ast.dump(function.args), ast.dump(function.returns) if function.returns else None
    return a.name == b.name and body(a) == body(b)


def drop_copied_skills(code: str, library) -> str:
    """The code without the definitions it copied from saved Skills, so that the saved Skills are called instead.

    A local model shown a Skill often writes its definition out again instead of calling it. When the copy is the
    same function as the saved version, the definition is removed, and linking puts the saved one in front. A
    definition that differs is a new version of the Skill and is kept.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    saved = set(library.names())
    lines = code.splitlines(keepends=True)
    for function in reversed(_functions(tree)):
        if function.name not in saved or not isinstance(function, ast.FunctionDef):
            continue
        original = next(node for node in ast.parse(library.get(function.name).code).body if isinstance(node, ast.FunctionDef))
        if _same_function(function, original):
            start = (function.decorator_list[0].lineno if function.decorator_list else function.lineno) - 1
            del lines[start:function.end_lineno]
    result = ''.join(lines)
    return re.sub(r'\n{3,}', '\n\n', result).strip('\n') if result != code else code


def only_calls_a_saved_skill(code: str, library) -> str | None:
    """The saved Skill a function does nothing but call (its body, apart from the docstring, is one return of a call
    of it), or None. Such a function is another name for the saved Skill and is not saved as a Skill of its own."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    main = _main_function(tree)
    if main is None:
        return None
    body = main.body[1:] if ast.get_docstring(main) is not None else main.body
    if len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call) \
            and isinstance(body[0].value.func, ast.Name) and body[0].value.func.id in set(library.names()):
        return body[0].value.func.id
    return None
