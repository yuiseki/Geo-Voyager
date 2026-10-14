"""Two mistakes the code of a local aggregation must not make, found without a model.

A local aggregation works only on the Observations of earlier steps. Two things have gone wrong in it:
- a measurement that is not there is turned into a value: o.get("count", 0). A lookup that found the wrong
  object then reads as a count of 0, and the comparison on top of it as a tie;
- an Observation is picked by its place in the list: decoded[2]. The order of the steps is not what the
  Observation means, and it changes when a step is repeated or the Planner plans another way.
The remedy is the same as for a target: find the object by its name and id, and let a missing field raise.
"""
import ast
import re


def _mentions(node: ast.AST, names: set[str]) -> bool:
    return any(isinstance(item, ast.Name) and item.id in names for item in ast.walk(node))


def _filters(node: ast.AST) -> bool:
    """A comprehension with an if: its result is a selection by a condition, and its first item is not a place in the list."""
    return isinstance(node, (ast.ListComp, ast.GeneratorExp, ast.SetComp)) and any(g.ifs for g in node.generators)


def _is_position(node: ast.AST) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        node = node.operand
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


def _is_false_default(node: ast.AST) -> bool:
    """A default that passes for a measurement: a number or None. An empty string (a label) or an empty list or dict is only 'nothing there'."""
    return isinstance(node, ast.Constant) and (node.value is None or
                                               (isinstance(node.value, (int, float)) and not isinstance(node.value, bool)))


def local_aggregation_violations(code: str, observation_count: int | None = None) -> list[str]:
    """The defaulted measurements and the positional picks of Observations, as written. Empty if the code does not parse.

    With exactly one earlier Observation there is nothing to choose between, and previous_observations[0] is simply
    that Observation (the Generator is shown it that way). Position is a mistake only when there are several.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    observations = {'previous_observations'}
    functions = {node.name: node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    for _ in range(3):                         # decoded = [json.loads(t) for t in previous_observations], rows = list(decoded)
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and _mentions(node.value, observations) and not _filters(node.value):
                observations.update(target.id for target in node.targets if isinstance(target, ast.Name))
            # the Observations passed to a function of the code: its parameter holds them inside it
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in functions:
                parameters = [arg.arg for arg in functions[node.func.id].args.args]
                for parameter, argument in zip(parameters, node.args):
                    if _mentions(argument, observations) and not _filters(argument):
                        observations.add(parameter)
                for keyword in node.keywords:
                    if keyword.arg and _mentions(keyword.value, observations) and not _filters(keyword.value):
                        observations.add(keyword.arg)
    found = []
    for node in ast.walk(tree):
        if observation_count != 1 and isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) \
                and node.value.id in observations and _is_position(node.slice):
            found.append(ast.unparse(node))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get' \
                and len(node.args) == 2 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str) \
                and _is_false_default(node.args[1]):
            found.append(ast.unparse(node))
    return found


def _is_input(node: ast.AST) -> bool:
    """results["name"]: an input of the step, a list of rows when the earlier step returned one."""
    return isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id == 'results' \
        and isinstance(node.slice, ast.Constant) and isinstance(node.slice.value, str)


def positional_input_picks(code: str) -> list[str]:
    """The rows of an input picked by their place: wards[0], or ids[0] of a list made from every row.

    An input is the whole of what an earlier step found (the 23 wards), and its order means nothing. Code that
    takes its first row answers for one row and still prints a value that looks like the answer for all: in
    memory_run1b, goal 4 counted the footways of 豊島区 alone, 2,463 of 93,108, and the Critic passed it.
    A row selected by a condition, a field of one row, and a response of a service are not inputs. Empty if the code
    does not parse.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    rows: set[str] = set()

    def is_rows(node: ast.AST) -> bool:
        if _is_input(node) or (isinstance(node, ast.Name) and node.id in rows):
            return True
        return isinstance(node, (ast.ListComp, ast.GeneratorExp)) and not _filters(node) \
            and any(is_rows(generator.iter) for generator in node.generators)

    for _ in range(3):
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign) and is_rows(node.value):
                rows.update(target.id for target in node.targets if isinstance(target, ast.Name))
            if isinstance(node, ast.For) and is_rows(node.iter) and isinstance(node.target, ast.Name):
                # a list that gets a value made from each row holds every row, in the input's order
                per_row = {node.target.id}
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Assign) and _mentions(inner.value, per_row):
                        per_row.update(target.id for target in inner.targets if isinstance(target, ast.Name))
                for inner in ast.walk(node):
                    if isinstance(inner, ast.Call) and isinstance(inner.func, ast.Attribute) and inner.func.attr == 'append' \
                            and isinstance(inner.func.value, ast.Name) and any(_mentions(arg, per_row) for arg in inner.args):
                        rows.add(inner.func.value.id)
    picks = [node for node in ast.walk(tree)
             if isinstance(node, ast.Subscript) and is_rows(node.value) and _is_position(node.slice)]
    whole = _every_place_of_a_checked_length(tree, picks)
    return [ast.unparse(node) for node in picks if ast.unparse(node.value) not in whole]


def _checked_lengths(tree: ast.AST) -> dict[str, set[int]]:
    """len(x) == k or len(x) != k anywhere in the code (either side): {x: {k}}."""
    lengths: dict[str, set[int]] = {}
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Compare) and len(node.ops) == 1 and isinstance(node.ops[0], (ast.Eq, ast.NotEq))):
            continue
        for sized, size in ((node.left, node.comparators[0]), (node.comparators[0], node.left)):
            if isinstance(sized, ast.Call) and isinstance(sized.func, ast.Name) and sized.func.id == 'len' \
                    and len(sized.args) == 1 and isinstance(size, ast.Constant) and type(size.value) is int:
                lengths.setdefault(ast.unparse(sized.args[0]), set()).add(size.value)
    return lengths


def _every_place_of_a_checked_length(tree: ast.AST, picks: list[ast.Subscript]) -> set[str]:
    """The inputs whose length the code checks to be k and whose rows 0 to k-1 it all takes by place: the start and
    the end of a route. Every row is used, so no place is a choice (a_run3, Goal 5). Taking row 0 of 23 checked
    wards is still a choice."""
    places: dict[str, set[int]] = {}
    for node in picks:
        index = node.slice.value if isinstance(node.slice, ast.Constant) else None
        places.setdefault(ast.unparse(node.value), set()).add(index)
    lengths = _checked_lengths(tree)
    return {rows for rows, taken in places.items() if any(taken == set(range(k)) for k in lengths.get(rows, ()))}


# The sphere and spheroid functions of DuckDB 1.5.6 read a point as latitude, longitude; read_table gives longitude,
# latitude (OGC:CRS84). Unflipped, Tokyo to Osaka (396 km) is 473 km and the area of Japan is NaN (2026-10-15).
LATITUDE_FIRST = ('ST_Distance_Sphere', 'ST_Distance_Spheroid', 'ST_DWithin_Spheroid', 'ST_Area_Spheroid',
                  'ST_Length_Spheroid', 'ST_Perimeter_Spheroid')


def axis_order_problems(code: str) -> list[str]:
    """The sphere and spheroid functions the code calls without flipping the coordinates anywhere."""
    if 'ST_FlipCoordinates' in code:
        return []
    return [f'{function} は緯度、経度の順の点を読む。read_table の geometry は経度、緯度なので、'
            f'ST_FlipCoordinates で入れ替えてから渡す（入れ替えないと、値は黙って誤る）'
            for function in LATITUDE_FIRST if re.search(rf'\b{function}\s*\(', code)]


def catalog_path_problems(code: str) -> list[str]:
    """The population grid's catalog path (files.cog_path) opened as a raster: it is a path in the dataset's
    repository, which the sandbox can not reach; the readable grid is behind dataset_url."""
    if 'cog_path' in code and re.search(r'rasterio\.open\s*\(', code) and 'dataset_url' not in code:
        return ['files の cog_path は原本の目録のパスで、実行環境からは開けない。画素は '
                "rasterio.open('/vsicurl/' + dataset_url('yuiseki/worldpop-jp-2026-01')) で開く"]
    return []
