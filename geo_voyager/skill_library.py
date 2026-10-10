"""Skills kept by name, with versions, and linked into the programs that call them.

A Skill (geo_voyager.skill_function) is one named function. Saving the same name again keeps the older code as an
earlier version. A Skill may call other saved Skills; link() puts every Skill a program calls, and the Skills those
call, in front of the program, each once and callees first, so the result runs as one script in the sandbox.
"""
import ast
from pathlib import Path

from .skill_function import SkillFunction, called_names, parse_skill


class SkillLibrary:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    def names(self) -> list[str]:
        if not self.root.is_dir():
            return []
        return sorted(directory.name for directory in self.root.iterdir() if self.versions(directory.name))

    def versions(self, name: str) -> list[int]:
        directory = self.root / name
        if not directory.is_dir():
            return []
        return sorted(int(path.name[1:]) for path in directory.iterdir()
                      if path.name.startswith('v') and path.name[1:].isdigit() and (path / 'code.py').is_file())

    def version_dir(self, name: str, version: int | None = None) -> Path:
        versions = self.versions(name)
        if not versions or (version is not None and version not in versions):
            raise KeyError(name)
        return self.root / name / f'v{version or versions[-1]}'

    def get(self, name: str, version: int | None = None) -> SkillFunction:
        versions = self.versions(name)
        if not versions or (version is not None and version not in versions):
            raise KeyError(name)
        return parse_skill((self.root / name / f'v{version or versions[-1]}' / 'code.py').read_text(encoding='utf-8'))

    def all(self) -> list[SkillFunction]:
        return [self.get(name) for name in self.names()]

    def add(self, code: str) -> int:
        """Save a Skill and return its version. The same code as the latest version is not saved again."""
        skill = parse_skill(code)
        unknown = [name for name in skill.calls if name not in self.names() and not _is_primitive(name, skill.code)]
        if unknown:
            raise ValueError(f'The Skill {skill.name} calls names that are neither saved Skills nor imported: {unknown}')
        versions = self.versions(skill.name)
        if versions and self.get(skill.name).code == skill.code:
            return versions[-1]
        version = (versions[-1] if versions else 0) + 1
        directory = self.root / skill.name / f'v{version}'
        directory.mkdir(parents=True)
        (directory / 'code.py').write_text(skill.code + '\n', encoding='utf-8')
        (directory / 'description.txt').write_text(skill.description + '\n', encoding='utf-8')
        return version


def _is_primitive(name: str, code: str) -> bool:
    """A name the Skill imports itself (a Control Primitive or a library function)."""
    tree = ast.parse(code)
    return any((alias.asname or alias.name).split('.')[0] == name
               for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names)


def linked_skills(program: str, library: SkillLibrary) -> list[str]:
    """The saved Skills link() puts in front of the program, as 'name@vN', callees first."""
    linked = link(program, library)
    if linked == program:
        return []
    names = [node.name for node in ast.parse(linked[:len(linked) - len(program)]).body if isinstance(node, ast.FunctionDef)]
    return [f'{name}@v{library.versions(name)[-1]}' for name in names]


def link(program: str, library: SkillLibrary) -> str:
    """The program with every Skill it calls (and their callees) defined in front of it, callees first."""
    try:
        tree = ast.parse(program)
    except SyntaxError:
        return program          # the sandbox reports the syntax error against the code as written
    defined = {node.name for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    saved = set(library.names())
    order: list[SkillFunction] = []
    visiting: set[str] = set()

    def visit(name: str) -> None:
        if name in visiting:
            raise ValueError(f'Skills call each other in a cycle through {name}')
        if any(skill.name == name for skill in order):
            return
        visiting.add(name)
        skill = library.get(name)
        for callee in skill.calls:
            if callee in saved:
                visit(callee)
        visiting.discard(name)
        order.append(skill)

    for name in called_names(tree, defined):
        if name in saved:
            visit(name)
    if not order:
        return program
    return '\n\n\n'.join([skill.code for skill in order] + [program])
