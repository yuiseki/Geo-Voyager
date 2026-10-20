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


def _root_name(node: ast.AST) -> str | None:
    """The name a chain of calls starts from: wards in wards.filter("x").project("y")."""
    while isinstance(node, (ast.Call, ast.Attribute)):
        node = node.func if isinstance(node, ast.Call) else node.value
    return node.id if isinstance(node, ast.Name) else None


def relation_in_sql_problems(code: str) -> list[str]:
    """The DuckDB relations put into a query with an f-string: FROM {wards} puts the relation's printed table, boxes
    and all, into the SQL, a syntax error (explores 13, 23, 32, 33, 36). The query reads a relation by its variable's
    name."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    relations: set[str] = set()
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)]
    changed = True
    while changed:
        changed = False
        for node in assignments:
            root = _root_name(node.value)
            if isinstance(node.value.func, ast.Attribute) and node.value.func.attr.startswith(('fetch', 'df', 'pl', 'arrow')):
                continue            # rows read out of a relation are values, not a relation
            is_relation = ('read_table' in {getattr(call.func, 'id', None) for call in ast.walk(node.value) if isinstance(call, ast.Call)}
                           or root in relations or (root == 'connection' and _calls_sql(node.value)))
            for target in node.targets:
                if is_relation and isinstance(target, ast.Name) and target.id not in relations:
                    relations.add(target.id)
                    changed = True
    put = dict.fromkeys(value.value.id for joined in ast.walk(tree) if isinstance(joined, ast.JoinedStr)
                        for value in joined.values
                        if isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) and value.value.id in relations)
    shapes = _geometries_read_out(tree)
    put_shapes = dict.fromkeys(value.value.id for joined in ast.walk(tree) if isinstance(joined, ast.JoinedStr)
                               for value in joined.values
                               if isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name) and value.value.id in shapes)
    return ([f'{name} は DuckDB の relation で、f-string で SQL に埋めると表を印字した文字列になり、構文エラーになる。'
             f'SQL には変数名をそのまま書く（FROM {name}）' for name in put]
            + [f'{name} は fetchone() で取り出した geometry（WKB のバイト列）で、f-string で SQL に埋めると構文エラーになる。'
               'geometry は Python に取り出さず、その表を SQL の中で JOIN するか副問い合わせで読む' for name in put_shapes])


_GEOMETRY_COLUMNS = ('geometry', 'way', 'geom')
# Spatial functions whose value is not a geometry: a number, a truth value or a text.
_SCALAR_FUNCTIONS = re.compile(r'ST_(?:X|Y|Z|M|XMin|XMax|YMin|YMax|Area|Area_Spheroid|Length|Length_Spheroid|Perimeter|'
                               r'Perimeter_Spheroid|Distance|Distance_Sphere|Distance_Spheroid|DWithin|NPoints|NumPoints|'
                               r'NumGeometries|Dimension|GeometryType|IsValid|IsEmpty|IsClosed|IsSimple|SRID|As\w*|'
                               r'Contains|Within|Intersects|Covers|CoveredBy|Crosses|Touches|Overlaps|Equals|Disjoint|'
                               r'Hilbert|QuadKey)\s*\(', re.IGNORECASE)


def _is_geometry(column: str) -> bool:
    """Whether a column of a SELECT list or project() is a geometry: way, w.geometry, ST_Union_Agg(way) AS shape."""
    column = column.strip()
    alias = re.search(r'\s+AS\s+"?(\w+)"?$', column, re.IGNORECASE)
    expression = column[:alias.start()].strip() if alias else column
    if (alias.group(1) if alias else expression.split('.')[-1]).strip('"').lower() in _GEOMETRY_COLUMNS:
        return True
    if re.fullmatch(r'(?:\w+\.)?"?(?:way|geometry|geom)"?', expression, re.IGNORECASE):
        return True
    return bool(re.match(r'ST_\w+\s*\(', expression, re.IGNORECASE)) and not _SCALAR_FUNCTIONS.match(expression)


def _split_top_level(text: str) -> list[str]:
    parts, depth, begin = [], 0, 0
    for index, char in enumerate(text):
        depth += (char == '(') - (char == ')')
        if char == ',' and depth == 0:
            parts.append(text[begin:index])
            begin = index + 1
    return parts + [text[begin:]]


def _selected(sql: str) -> list[str] | None:
    """The columns of a query's first SELECT list, read up to its FROM outside any parentheses."""
    found = re.search(r'\bSELECT\b', sql, re.IGNORECASE)
    if not found:
        return None
    depth = 0
    for index in range(found.end(), len(sql)):
        depth += (sql[index] == '(') - (sql[index] == ')')
        if depth == 0 and re.match(r'\bFROM\b', sql[index:], re.IGNORECASE) and not re.match(r'\w', sql[index - 1]):
            return _split_top_level(sql[found.end():index])
    return _split_top_level(sql[found.end():])


def _string_text(node: ast.AST, strings: dict[str, str]) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return ''.join(value.value if isinstance(value, ast.Constant) else '{}' for value in node.values)
    if isinstance(node, ast.Name):
        return strings.get(node.id)
    return None


def _projected(node: ast.AST, strings: dict[str, str] | None = None) -> list[str] | None:
    """Whether each column of x.project("a, b, geometry").fetchone() or connection.sql(query).fetchone() is a
    geometry, or None when the call reads no such row."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'fetchone'):
        return None
    for call in ast.walk(node):
        if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.args):
            continue
        if call.func.attr == 'project' and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
            return [_is_geometry(column) for column in _split_top_level(call.args[0].value)]
        if call.func.attr in ('sql', 'query', 'execute'):
            sql = _string_text(call.args[0], strings or {})
            columns = _selected(sql) if sql is not None else None
            if columns is not None:
                return [_is_geometry(column) for column in columns]
    return None


def _geometries_read_out(tree: ast.AST) -> set[str]:
    """The names a row's geometry column is read into: _, _, shape = rel.project("a, b, geometry").fetchone(), or
    shape = row[0] of row = connection.sql("SELECT ST_Union_Agg(way) ...").fetchone()."""
    assigns = [node for node in ast.walk(tree) if isinstance(node, ast.Assign) and len(node.targets) == 1]
    strings = {node.targets[0].id: text for node in assigns if isinstance(node.targets[0], ast.Name)
               for text in [_string_text(node.value, {})] if text is not None}
    rows = {}
    for node in assigns:
        columns = _projected(node.value, strings)
        if columns is not None and isinstance(node.targets[0], ast.Name):
            rows[node.targets[0].id] = columns

    def columns_of(value: ast.AST) -> list[bool] | None:
        return rows.get(value.id) if isinstance(value, ast.Name) else _projected(value, strings)

    names = set()
    for node in assigns:
        target, value = node.targets[0], node.value
        if isinstance(target, ast.Tuple):
            columns = columns_of(value)
            if columns is not None and len(columns) == len(target.elts):
                names.update(element.id for element, geometry in zip(target.elts, columns)
                             if isinstance(element, ast.Name) and geometry)
        elif (isinstance(target, ast.Name) and isinstance(value, ast.Subscript) and isinstance(value.slice, ast.Constant)
              and isinstance(value.slice.value, int)):
            columns = columns_of(value.value)
            if columns is not None and -len(columns) <= value.slice.value < len(columns) and columns[value.slice.value]:
                names.add(target.id)
    return names


def _calls_sql(node: ast.Call) -> bool:
    return any(isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute) and call.func.attr in ('sql', 'query')
               for call in ast.walk(node))


_TARGET_KEYS = ('name', 'id_type', 'id_value')


def target_key_problems(code: str) -> list[str]:
    """The keys read from intent_target that it does not have: it has name, id_type and id_value, and the code read
    intent_target["relation_id"], a KeyError that took two steps (explores 35, 37)."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []
    assigned = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    targets = {'intent_target'}
    changed = True
    while changed:
        changed = False
        for node in assigned:
            if isinstance(node.value, ast.Name) and node.value.id in targets:
                for name in node.targets:
                    if isinstance(name, ast.Name) and name.id not in targets:
                        targets.add(name.id)
                        changed = True
    # a name bound to anything else may hold another dict
    targets -= {name.id for node in assigned if not (isinstance(node.value, ast.Name) and node.value.id in targets)
                for name in node.targets if isinstance(name, ast.Name)}
    # a key asked after first ("relation_id" in intent_target) is a guess that is not taken when wrong
    asked = {node.left.value for node in ast.walk(tree) if isinstance(node, ast.Compare) and isinstance(node.left, ast.Constant)
             and any(isinstance(op, (ast.In, ast.NotIn)) for op in node.ops)}
    read = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name) and node.value.id in targets:
            key = node.slice
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get'
              and isinstance(node.func.value, ast.Name) and node.func.value.id in targets and len(node.args) == 1):
            key = node.args[0]          # with a default, a guess that falls back
        else:
            continue
        if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value not in _TARGET_KEYS + tuple(asked):
            read.append((node.lineno, node.col_offset, key.value))
    return [f'intent_target に "{key}" は無い。intent_target が持つのは name、id_type、id_value だけ。'
            f'対象の ID は intent_target["id_value"]（その種類が intent_target["id_type"]）'
            for key in dict.fromkeys(key for _line, _column, key in sorted(read))]
