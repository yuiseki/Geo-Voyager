"""Replies of a stub model for the tests of the code generation."""


def reply_reading(intent, fallback):
    """A valid reply whose code reads exactly the Datasets the Intent declares, as the contract requires."""
    from geo_voyager.skill_candidate import PRIMITIVE_DATASETS
    readers = [name for name, dataset in PRIMITIVE_DATASETS.items() if dataset in intent.dataset_ids]
    if not readers:
        return fallback
    calls = ''.join(f'        {name}(connection)\n' for name in readers)
    return ('説明:\nS\n---\nコード:\n```python\n'
            f'from geo_voyager.control_primitives import connect_duckdb, {", ".join(readers)}\n\n'
            f'def answer():\n    """Answer."""\n    with connect_duckdb() as connection:\n{calls}        return 1\n```')
