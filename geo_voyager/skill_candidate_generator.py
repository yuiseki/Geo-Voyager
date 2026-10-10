
from .id_type_literals import id_type_comparisons
from .intent import Intent
from .local_aggregation_contract import local_aggregation_violations
from .skill_candidate import entry_problems, main_function_name, skill_shape_problems
from .place_names import place_words_in
from .skill_function import SkillFunction
from .llama_client import LlamaClient
from .skill_candidate import SkillCandidate
from .services import load_service_graph
from .observation_context import describe_observations


def _parse_candidate(text: str) -> SkillCandidate:
    lines = text.strip().splitlines()
    if not lines or lines[0] != '説明:' or lines.count('---') != 1:
        raise ValueError('Candidate must contain 説明: and a single --- separator')
    separator = lines.index('---')
    code_block = '\n'.join(lines[separator + 1:]).strip()
    # A local model sometimes drops the colon ('コード' alone on its line); the fence below still marks the code.
    if not (code_block.startswith('コード:') or code_block.startswith('コード\n')):
        raise ValueError('Candidate must contain コード:')
    fenced = code_block.removeprefix('コード:').removeprefix('コード').strip().splitlines()
    if len(fenced) < 2 or fenced[0] != '```python' or fenced[-1] != '```':
        raise ValueError('Candidate code must use a Python code fence')
    head = lines[1:separator]
    # 計画: (the plan, as in Voyager's response) is read but not kept in the description
    description = '\n'.join(head[:head.index('計画:')] if '計画:' in head else head).strip()
    code_lines = fenced[1:-1]
    code = '\n'.join(code_lines).strip()
    if not description or not code or any(line.startswith('```') for line in code_lines):
        raise ValueError('Candidate description and code must be non-empty and correctly fenced')
    return SkillCandidate(code=code, description=description)


MAX_ID_TYPE_RETRIES = 2

RESPONSE_FORMAT = ('返答は次の形式だけ。前置きや追記は禁止。1行目は必ず「説明:」だけ。説明本文は2行目から 1 文で書く。\n'
                   '「計画:」の下に、どの Skill や Primitive をどの順で使うかを番号つきで短く書く。\n'
                   '説明:\n<何をする関数か>\n計画:\n1) ...\n2) ...\n---\nコード:\n```python\n'
                   'from geo_voyager.control_primitives import call_service\n'
                   '\n\ndef <何をするかが分かる名前>(<実行環境が渡す値>, <既定値つきの引数>):\n'
                   '    """<何をするか>"""\n'
                   '    ...\n'
                   '    return <結果>\n```\n')


def _id_type_note(found: list[str]) -> str:
    return ('\n\n前回の応答は拒否された。コードが id_type を固定の文字列と比べている: ' + '; '.join(found)
            + '。id_type の綴りを推測した分岐は、外れると何も起きずに誤った値（0 件など）になる。'
              'id_type と比べず、intent_target["id_value"] をそのまま使う（Overpass の area は int(intent_target["id_value"]) + 3600000000）。')


def _local_note(found: list[str]) -> str:
    return ('\n\n前回の応答は拒否された。ローカル集計のコードが契約を破っている: ' + '; '.join(found)
            + '。測定値の欠落を get の既定値（0 など）で代用しない。Observation を番号や位置で選ばない。'
              '前段の object は name と ID で選び（条件で絞った一覧の先頭は可）、必須のキーは [] で取り、無ければ例外にする。')


def _shape_note(found: list[str]) -> str:
    return ('\n\n前回の応答は拒否された。新しい関数が Skill の形になっていない: ' + '; '.join(found)
            + '。新しい処理は、名前と引数と docstring を持つ関数 1 つにまとめる。実行時変数は関数の中で読まず、関数を呼ぶ行で引数として渡す。')


def skills_section(skills: list[SkillFunction] | tuple = ()) -> str:
    """The saved Skills the code may call, shown first, as Voyager shows its retrieved programs."""
    if not skills:
        return ''
    listed = '\n\n'.join(f'# Skill: {skill.name}\n{skill.code}' for skill in skills)
    return ('以下は、これまでに成功して保存された役に立つ関数（Skill）です。実行時に定義済みなので、import も定義も不要で、'
            '名前で呼べます。\n```python\n' + listed + '\n```\n\n')


def harness_section(intent: Intent) -> str:
    """What the environment does with the function, shown first. A probe of the local model found that it knew how
    its function is called and that a shown Skill can be called by name, but not that its function is saved and
    called again by later Intents, nor how conditions reach a function (docs/harness_understanding.md)."""
    runtime = ([*(['dataset_id'] if intent.dataset_ids else []), *(['intent_target'] if intent.target is not None else []),
                *(['previous_observations', 'intent_text'] if intent.previous_observations else [])])
    passed = ('実行環境が引数として渡すのは、この Intent では ' + '、'.join(runtime) + ' だけ。それ以外の引数には既定値を付ける。'
              if runtime else '実行環境はこの Intent では値を何も渡さない。引数には全て既定値を付ける。')
    if intent.target is not None:
        example = ('  def count_tag_in_area(intent_target, key="amenity", value="cafe"):\n'
                   '  なら、後の Intent「新宿区のホテルの数」では、次の関数だけを書けばよい:\n'
                   '  def count_hotels_in_area(intent_target, key="tourism", value="hotel"):\n'
                   '      """対象の区域の tourism=hotel の地物数を返す。"""\n'
                   '      return count_tag_in_area(intent_target, key=key, value=value)\n')
    else:
        example = ('  def tag_usage_count(key="cuisine", value="ramen"):\n'
                   '  なら、後の Intent「cuisine=sushi の使用数」では、次の関数だけを書けばよい:\n'
                   '  def sushi_usage_count(key="cuisine", value="sushi"):\n'
                   '      """cuisine=sushi の使用数を返す。"""\n'
                   '      return tag_usage_count(key=key, value=value)\n')
    return ('この環境の仕組み（最初に読む）:\n'
            '- Intent ごとに、Python の関数を 1 つ書く。実行環境がその関数を呼び、戻り値を JSON で出力する。\n'
            '- 実行が成功し、Intent に答えたと判定されると、その関数は関数名のまま Skill として保存される。'
            '後の別の Intent では、近い Skill が「保存済みの関数」として見せられ、新しい関数の中から名前で、引数を変えて呼ばれる。'
            'つまり、いま書く関数は、後で部品として別の引数で呼ばれる。\n'
            f'- {passed}\n'
            '- 条件（タグ、件数、移動手段など）は既定値つきの引数で受け取り、既定値に今回の値を書く。'
            '後の Intent の関数は、その引数に別の値を渡して呼ぶ。対象の名前や今回の条件を、関数名や関数の中に書き込まない。\n'
            '- 例: 保存済みの Skill が\n' + example + '\n')


def skill_rules(intent: Intent) -> str:
    """How to write the code, numbered as in Voyager's action prompt."""
    runtime = ([*(['dataset_id'] if intent.dataset_ids else []), *(['intent_target'] if intent.target is not None else []),
                *(['previous_observations', 'intent_text'] if intent.previous_observations else [])])
    arguments = ('、'.join(runtime) + ' だけ。これらは関数の中で直接読まず、引数として受け取る' if runtime
                 else 'ない。引数を取るなら既定値を付ける')
    return ('\nコードの決まり:\n'
            '1) 名前と引数と docstring（何をするかの 1〜3 文）を持つ関数を 1 つ書く。トップレベルには import と、その関数の定義だけを書く。'
            '実行環境がその関数を呼び、戻り値（dict や list など JSON にできる値）を JSON で出力する。関数を呼ぶ行や print は書かない。\n'
            f'2) 実行環境が引数として渡せる値は {arguments}。それ以外の引数には既定値を付ける。\n'
            '3) 上に Skill があれば、できるだけ呼んで再利用する。Skill の定義を書き写さない。\n'
            '4) 関数は後で別の Intent から部品として呼ばれる。対象・条件・データは引数で受け取り、汎用に書く。答えの値を埋め込まない。\n'
            '5) 結果は return で返す。必須の値が無ければ例外にし、既定値で成功を装わない。\n'
            '6) 関数名は、何をするかが分かる名前にする。\n')


def contract_problems(intent: Intent, code: str, shown: tuple[str, ...] = ()) -> list[tuple[str, str]]:
    """What the code breaks, as (the code found, the note for the model), for the kinds of Intent that have a contract."""
    problems = []
    shape = entry_problems(code) or skill_shape_problems(code, shown)
    name = main_function_name(code)
    places = place_words_in(name, intent.target.name if intent.target is not None else None) if name else []
    if places:
        shape = shape + [f'関数名 {name} に場所の名前（{", ".join(places)}）が入っている。関数は後で別の場所にも使われる部品なので、'
                         '何をするかで名付け（例: count_tag_in_area）、場所は intent_target で受け取る']
    if shape:
        problems.append(('skill shape: ' + '; '.join(shape), _shape_note(shape)))
    if intent.target is not None and intent.target.resolved:
        found = id_type_comparisons(code)
        if found:
            problems.append(('id_type: ' + '; '.join(found), _id_type_note(found)))
    if intent.requires_context:
        found = local_aggregation_violations(code, len(intent.previous_observations))
        if found:
            problems.append(('local aggregation: ' + '; '.join(found), _local_note(found)))
    return problems


class SkillCandidateGenerator:
    def __init__(self, llm_client: LlamaClient | None = None) -> None:
        self.llm_client = llm_client if llm_client is not None else LlamaClient()

    def generate(self, intent: Intent, skills: list[SkillFunction] | tuple = ()) -> SkillCandidate:
        shown = tuple(skill.name for skill in skills)
        datasets = '\n'.join(f'- {dataset_id}' for dataset_id in intent.dataset_ids)
        prompt = (
            'Intent を完遂する Python の関数と簡潔な説明を書いてください。\n'
            '利用可能な Control Primitives（geo_voyager.control_primitives から import）:\n'
            '- connect_duckdb(): sandbox 用 DuckDB 接続を返す。with で接続を管理する。\n'
            '- dataset_url(dataset_id): 登録済み行政区・駅 Dataset の Gateway URL を返す。\n'
            '- load_admin_units(dataset_id, connection, area=None): Gateway 経由で行政区域の DuckDB relation を返す。\n'
            'relation の列は code5（5桁文字列の行政コード）、name（区域名）、population（整数の人口）。\n'
            'area=None は全行政区域を返す。area="東京都23区" は23区だけを返す。未対応 area は失敗する。\n'
            '東京都23区には load_admin_units(dataset_id, connection, area="東京都23区") を使う。\n'
            '行政コードを推測・生成しない。AOI の絞り込みは Primitive に任せる。\n'
            '- load_stations(dataset_id, connection): Gateway 経由で駅の DuckDB relation を返す。\n'
            '駅 relation の列は name（駅名）、latitude（緯度）、longitude（経度）。\n'
            '行政区域 Dataset には load_admin_units、駅 Dataset には load_stations を使う。\n'
            '返り値は DuckDB relation であり pandas DataFrame ではない。\n'

            'order(expression) は SQL の列名と ASC/DESC でソートする。limit(n) は行数を制限する。\n'
            'aggregate(expression) は SQL 集計式を受け取る。平均人口なら aggregate("avg(population) AS average_population")。\n'
            'fetchone() は現在の relation の列順の tuple または None を返す。\n'
            '集計後の値は fetchone()[0] で取得する。集計前の行政区域は (code5, name, population)。\n'
            'DataFrame の添字、between、sort_values、head、iloc は使えない。\n\n'
            '制約:\n'
            '- Primitive はグローバルには存在しない。必ずコードで明示的に import する。\n'
            '- Primitive 名を変更・推測しない。提示した名前・綴りをそのまま使う。\n'
            'from geo_voyager.control_primitives import connect_duckdb, load_admin_units, load_stations\n'
            '- Dataset へのアクセスは Control Primitives のみ使う。\n'
            '- 外部URLを直接使わない。HTTP や read_parquet を直接呼ばない。\n'
            '- 結果は return で返す。選択・集計の意味が分かるキーと具体的な回答値を持つ dict にする。\n'
            '例えば最小人口なら、{"name": 区名, "population": 人口} を返す。\n'
            '- dataset_id は実行環境から関数の引数として与えられる。\n'
            'dataset_id = ... という代入を書かない。Dataset ids は利用範囲のメタデータでありコードへ埋め込まない。\n'
            '- 再利用可能な分析コードにする。答えの区名や人口を埋め込まない。\n'
            '- 標準 Python と上記 Primitive・DuckDB relation の操作だけで実装する。\n'
            '- UUID 生成や Skill の保存はしない。\n'
            '- 1件だけ生成し、前置きや追記を付けない。\n\n'
            '接続部分の例（with 行はこの形のまま使う。接続関数は connect_duckdb、duck の綴り）:\n'
            'from geo_voyager.control_primitives import connect_duckdb, load_admin_units, load_stations\n'
            'def <何をするかが分かる名前>(dataset_id):\n'
            '    """<何をするか>"""\n'
            '    with connect_duckdb() as connection:\n'
            '        # 行政区域なら load_admin_units(dataset_id, connection, area="東京都23区")\n'
            '        # 駅なら load_stations(dataset_id, connection)（import も追加する）\n'
            '        # Intent に必要な relation 操作をして、結果を return する\n\n'
            + skill_rules(intent) +
            f'Intent:\n{intent.text}\n\n利用する Dataset ids:\n{datasets}\n\n'
            + RESPONSE_FORMAT
        )
        graph = load_service_graph()
        available = [graph.get(service_id) for service_id in intent.service_ids] if intent.service_ids else ([] if intent.requires_context else graph.all())
        services = '\n'.join(
            f'- id: {service.id}; protocol: {service.protocol}; description: {service.description}'
            for service in available
        )
        service_contract = (
            '\n利用可能な登録済み Service（URL は Gateway が解決する）:\n'
            f'{services}\n'
            '- call_service(service_id, *, path="", params=None, body=None, content_type=None): '
            'Service Gateway を通して text を返す汎用 Primitive。\n'
            'body=None は GET、それ以外は POST。params は文字列の辞書。'
            'POST は body を文字列として渡し content_type を指定する。\n'
            'import json と urllib.parse.urlencode 等の標準ライブラリは利用可能。'
            '返答の JSON は json.loads で解析する。サービス固有のリクエストは Intent に応じて生成する。\n'
            'Service へのアクセスも call_service のみ使う。任意 URL や直接 HTTP は使わない。\n'
            'タグ探索の要求では辞書サービスから実行時にキー・値を調べ、得た結果を後続検索に使う。'
            'キー・値をコードに固定しない。返された data の key/value を変数として使う（Intent が条件を明示しているときは、その値を引数の既定値に書いてよい）。'
            '辞書が空なら失敗させ、既知のタグへ fallback しない。\n'
            'コードは短くする。複雑な三重引用符は避け、クエリ文字列の引用符を正しく閉じる。\n'
            f'Intent の Service ids: {", ".join(intent.service_ids)}\n'
        )
        if not intent.dataset_ids:
            prompt = (
                'Write one Python function that fulfills the Intent. Use precise API syntax, no speculation or unfinished code.\n'
                'description に対象・使用サービス・出力内容を含める。Intent の範囲を説明で省略しない。答えを説明へ固定しない。\n'
                'For tag discovery, choose one relevant dictionary result. Use its key and value together as variables in one equality filter, not a key-existence filter.\n'
                'Do not guess tags or use a hardcoded tag fallback. Do not make broad unfiltered geographic queries.\n'
                'Every call_service call must explicitly supply path, chosen from the registered endpoint paths above. Never omit path.\n'
                'call_service is not a global: you MUST import it with from geo_voyager.control_primitives import call_service.\n'
                'Return exactly one JSON-serialisable value for this Intent (the environment prints it as JSON); no headings or logs. Name each key for what its value is, for example '
                'value, count, distance_km, label. Never put a value under a key that means something else, such as a count or a tag key under relation_id.\n'
                'Return discovered keys/values when tag discovery is requested, inside the returned value.\n'
                'Write at most 40 lines of code. No comments, no speculation or alternative approaches.\n'
                'Before returning, check imports, every endpoint path, balanced square brackets in tag filters, and the protocol grammar.\n'
                '標準ライブラリと call_service のみで実装する。直接 HTTP や外部 URL を使わない。\n'
                'call_service の params は dict[str, str] をそのまま渡す。params を urlencode しない。\n'
                'body は str。フォーム本文を送る場合だけ urllib.parse.urlencode を使う。\n'
                '返答は JSON 本文の文字列なので json.loads で解析する。HTTP status_code フィールドを仮定しない。\n'
                '探索結果を変数に取り、後続サービスの問い合わせに使う。答えやタグを事前に固定しない。\n'
                '無駄なコメント・仮定・未実装の分岐は書かない。最終結果の具体的な回答を return で返す。\n'
                '結果が空なら例外にする。必須フィールドが無い場合も例外にし、N/A やデフォルト値で成功を装わない。\n'
                '後続が解析できるよう、戻り値は JSON にできる値（dict や list）にする。実行環境が JSON で出力する。キーは、その値が何かを表す意味の分かる名前にする（例: value、count、distance_km）。固定のスキーマはない。\n'
                '出力が対象（区域・地物など、安定した ID を持つ実体）の一覧や、その対象についての測定なら、各対象を name と relation_id 等の ID で出力し、'
                '順番を固定する。一意なIDと指定件数を assert し、合わなければ例外にする。'
                '対象でないもの（タグの値、件数のランキング、距離など）は、name や relation_id のキーを使わず、意味に沿ったキー（例: {"value": "pizza", "count": 132565}）で出力する。\n'
                'description は任意対象の測定という再利用可能な操作を説明し、対象の名前や答えを固定しない。\n'
                'UUID や Skill 保存処理を書かない。\n'
                + skill_rules(intent) +
                f'Intent:\n{intent.text}\n\n'
                + RESPONSE_FORMAT
            )
        if intent.requires_context:
            prompt += '\nローカル集計の Intent。外部サービスを呼ばず previous_observations のデータだけを解析・集計する。\n'
        if intent.previous_observations:
            prompt += ('\n前段 Observation の JSON の形（値は実行時に取得）:\n'
                       + describe_observations(intent.previous_observations)
                       + '\n実行環境の previous_observations は前段 stdout の list[str]。intent_text は現在の Intent 本文。'
                         '結果をコードへ埋め込まず、関数の引数として受け取ったこの値を実行時に解析して利用する。'
                         '再利用コードでは対象や番号を intent_text または前段データから取り出す。'
                         'previous_observations や intent_text を代入で上書きしない。json.loads(previous_observations[index]) を使う。'
                         '最終結果は意味の分かるキーを持つ値を return で返す。')
        if not intent.dataset_ids:
            if intent.target is not None:
                prompt += ('\nこの Intent は対象についての Intent なので、出力に対象の name と ID を含める。'
                           '測定（件数、合計など）なら、何を測ったか（条件）もキーで出力に含める。'
                           '例: {"name": "渋谷区", "relation_id": "1759477", "tag": "amenity=cafe", "count": 459}。'
                           '同じ対象を別の条件で測った出力を、後のローカル集計が区別できるようにするため。')
                prompt += ('\n最後の重要な制約: 対象は実行時変数 intent_target であり、Skill の固定対象ではありません。'
                           '説明に対象の名前を書かず、「実行時に指定された対象」と書いてください。'
                           '説明の例: 実行時に指定された対象について、指定条件に一致する地物の件数を取得する。')
                if intent.target.resolved:
                    prompt += ('使用サービス、条件、出力は説明に残す。コードは対象を ID で扱う。対象の主キーは intent_target["id_value"]'
                               '（ID の種類は intent_target["id_type"]）で、名前 intent_target["name"] は表示用。'
                               '名前は前段の Observation の名前と違っていてもよいので、名前の一致で対象を選ばない。名前もIDもコードへ固定しない。')
                    if intent.previous_observations:
                        prompt += ('\n前段 Observation の JSON（list でも単一の object でもよい）に対象の object があるときは、'
                                   'ID が一致するものを使う。ID が一致する object が無ければ例外にする。'
                                   '同じ名前でも ID が違う object は別の対象なので使わない。接続例:\n'
                                   'import json\n'
                                   'candidates = []\n'
                                   'for text in previous_observations:\n'
                                   '    value = json.loads(text)\n'
                                   '    candidates += value if isinstance(value, list) else [value]\n'
                                   'matches = [t for t in candidates if isinstance(t, dict) and str(t.get(intent_target["id_type"])) == intent_target["id_value"]]\n'
                                   'assert matches\n'
                                   'target = matches[0]\n'
                                   '対象の ID は intent_target["id_value"] から直接使ってもよい。')
                else:
                    prompt += ('使用サービス、条件、出力は説明に残す。コードは対象の名前を intent_target["name"] から取り、名前もIDもコードへ固定しない。')
                    if intent.previous_observations:
                        prompt += ('\n対象は名前で特定する。位置では選ばない。previous_observations の JSON（list でも単一の object でもよい）から、'
                                   'name が intent_target["name"] と完全一致する object を探し、その安定ID（relation_id など）を使う。'
                                   '同じ名前で同じIDの object は同一対象。一致する対象が無い、またはIDが異なる対象が複数あれば例外にする。接続例:\n'
                                   'import json\n'
                                   'candidates = []\n'
                                   'for text in previous_observations:\n'
                                   '    value = json.loads(text)\n'
                                   '    candidates += value if isinstance(value, list) else [value]\n'
                                   'matches = [t for t in candidates if isinstance(t, dict) and t.get("name") == intent_target["name"]]\n'
                                   'assert matches and len({t["relation_id"] for t in matches}) == 1\n'
                                   'target = matches[0]\n'
                                   'ID のキー名は前段の形に合わせる。この target からIDを取り、要求された測定を続ける。')
            if 'overpass' in intent.service_ids:
                prompt += ('\n件数測定の場合の抽象構文（メタ変数を実行時値へ置換）: '
                           '[out:json][timeout:12];nwr["<key>"="<value>"](area:<area_id>);out count;'
                           'キー比較は角括弧、地理区域指定はその後の丸括弧。上の構文の順序を保つ。'
                           )
                if intent.target is not None and intent.target.resolved:
                    prompt += ('<area_id> は、対象の OSM relation の ID（intent_target["id_value"]）を整数にして 3600000000 を足した値。'
                               'id_type を固定の文字列と比べない。id_type の綴りを推測した分岐は、外れると area が誤ったまま 0 件になる。')
                else:
                    prompt += '<area_id> は、対象の OSM relation の ID を整数にして 3600000000 を足した値。'
            if 'yuisekin-geosparql' in intent.service_ids:
                prompt += ('\n外部RelationIDが必要な場合の取得は ?ward gs:osmRelation ?relation 。'
                           'SELECT ?label ?relation の ?relation から正の数値IDを取る。'
                           '出力前に全IDについて str(relation_id).isdigit() を assert する。')
            if intent.requires_context:
                prompt += ('\nローカル集計の入力契約: 全 Observation を解析する接続例は '
                           'decoded = [json.loads(text) for text in previous_observations] 。'
                           '最初の対象一覧は対象メタデータであり、後続の各 JSON object が個別測定を持つ。'
                           '最初の一覧だけを測定結果全体とみなさない。形から必要な測定レコードを選び、全対象の測定が揃うことを assert する。'
                           '必須測定値は添字でアクセスし、欠落時は例外にする。get のデフォルト値や 0 で代用しない。'
                           'previous_observations や、それを解析した list の要素を、番号や位置で選ばない（previous_observations[2] や decoded[3] は禁止）。'
                           '対象の object は名前と ID で選ぶ。前段の番号は説明の表示であり、コードで番号によって選ばない。'
                           '同じ対象について複数の object があるときは、何を測ったかのキー（tag など）と、測定値のキーを持つ object を選ぶ'
                           '（例: [o for o in decoded if o.get("tag") == "amenity=cafe" and "count" in o]）。測定値を持たない object（ID だけの出力）は使わない。'
                           'その実測値を用いて Intent の集計・選択を実行する。')
            def generate_once(extra: str = '') -> SkillCandidate:
                return _parse_candidate(self.llm_client.generate(
                harness_section(intent) + skills_section(skills) + service_contract + prompt + extra, temperature=0.2, enable_thinking=True,
                max_tokens=3072, reasoning_budget_tokens=1024, assistant_prefix="説明:\n",
                system_prompt=(
                    'You are a precise Python programmer. Return exactly one description, a short plan and one Python function '
                    'in the requested format. Description must be one sentence. '
                    'Code must be short, with no comments, no speculation, no unfinished branches. '
                    'First line must be exactly 説明:, with description on the next line. '
                    'Use only the Service ids declared by the Intent. '
                    'Use the supplied API contracts literally. Explicitly import primitives. '
                    'When the Intent names a target, describe the operation on a runtime-resolved target, never on the current name. '
                    'The code MUST use the runtime variable intent_target. If it has id_value, that id (of type id_type) is the key and the name is only for display: never choose a target by its name, and if previous_observations exist, find the target there by that id. If it has only a name, take it from intent_target["name"] and match it against the name field of the objects. '
                    'Do not fix current IDs or names in code or description. '
                    'Discover answers from service responses, never invent them. Return the concrete results; the environment calls the function. '
                    'Reuse the saved Skills shown first as much as possible, by calling them; never copy their definitions. '
                    'Exact layout, with every label on a separate line:\n説明:\n<description>\n計画:\n1) ...\n---\nコード:\n```python\n<imports and one function>\n```'
                ),
            ))
            return self._keep_the_contract(intent, generate_once, shown)
        return self._keep_the_contract(
            intent, lambda extra='': _parse_candidate(self.llm_client.generate(harness_section(intent) + skills_section(skills) + service_contract + prompt + extra)), shown)

    @staticmethod
    def _keep_the_contract(intent: Intent, generate_once, shown: tuple[str, ...] = ()) -> SkillCandidate:
        """Generate, and generate again with the reason while the code breaks a contract. Refuse after the retries."""
        candidate = generate_once()
        for retry in range(MAX_ID_TYPE_RETRIES + 1):
            problems = contract_problems(intent, candidate.code, shown)
            if not problems:
                return candidate
            if retry == MAX_ID_TYPE_RETRIES:
                raise ValueError('Candidate breaks the code contract: ' + ' | '.join(found for found, _ in problems))
            candidate = generate_once(''.join(note for _, note in problems))
