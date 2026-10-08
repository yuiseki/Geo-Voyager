def dataset_url(dataset_id: str) -> str:
    if dataset_id not in ("yuiseki/jp-admin-2026-09", "yuiseki/ekidata-jp"):
        raise ValueError("Only the administrative and station datasets are supported")
    return f"http://gateway:8000/datasets/{dataset_id}"
