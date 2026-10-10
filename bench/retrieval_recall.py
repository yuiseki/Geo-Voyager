"""How often the Skill retriever would have shown an existing Skill of the same kind, on a stored carried-over run.

    PYTHONPATH=. .venv/bin/python -m bench.retrieval_recall RESULTS.jsonl LIBRARY_DIR

For each step whose Intent counts features or looks up an OSM relation ID, the library as it was before the step
(the seed Skills and the Skills learned by earlier steps, latest versions as stored at the end) is searched with the
Intent's text, by each embedding model. A hit is a Skill of the same kind in the top k. The kinds are named by
words in the Skill's name, which the stored runs use consistently (count_..., ..._relation_id...). No model call
other than embeddings.
"""
import json
import math
import re
import sys
from pathlib import Path

from geo_voyager.embedding_client import EmbeddingClient
from geo_voyager.skill_library import SkillLibrary

MODELS = {'granite-embedding': 'http://10.105.167.163:8080', 'embeddinggemma': 'http://localhost:30194'}
SEEDS = {'count_station_records', 'least_populous_area', 'most_populous_area', 'northernmost_station',
         'top_areas_by_population', 'total_population'}
KINDS = {
    'count': (re.compile(r'(地物数|件数を|の数)'), re.compile(r'^count_(?!station|4char|tokyo)')),
    'relation_id': (re.compile(r'relation ?ID', re.I), re.compile(r'relation_id')),
}


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b)) / (math.hypot(*a) * math.hypot(*b))


def main() -> None:
    results, root = Path(sys.argv[1]), Path(sys.argv[2])
    library = SkillLibrary(root)
    k = 4
    learned_before, cases = set(SEEDS), []
    for line in results.read_text().splitlines():
        row = json.loads(line)
        for step in row['steps']:
            for kind, (intent_words, name_words) in KINDS.items():
                if not intent_words.search(step['intent']):
                    continue
                pool = sorted(name for name in learned_before if name in library.names())
                same_kind = [name for name in pool if name_words.search(name)]
                if same_kind:
                    cases.append((kind, step['intent'], pool, same_kind))
            if step.get('learned_skill'):
                learned_before.add(step['learned_skill'].split('@')[0])
    print(f'{len(cases)} steps with a Skill of the same kind already in the library')
    descriptions = {name: library.get(name).description for name in library.names()}
    for model, url in MODELS.items():
        client = EmbeddingClient(url, model)
        names = sorted(descriptions)
        vectors = dict(zip(names, client.embed([descriptions[n] for n in names])))
        hits = {kind: [0, 0] for kind in KINDS}
        for kind, intent, pool, same_kind in cases:
            query = client.embed([intent])[0]
            top = sorted(pool, key=lambda name: -cosine(query, vectors[name]))[:k]
            hits[kind][0] += any(name in same_kind for name in top)
            hits[kind][1] += 1
        print(f'{model}: a Skill of the same kind in the top {k}: '
              + ', '.join(f'{kind} {hit} / {total}' for kind, (hit, total) in hits.items()))


if __name__ == '__main__':
    main()
