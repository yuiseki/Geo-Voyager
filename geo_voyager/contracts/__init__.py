"""The contracts the model's work is held to, checked without a model where they can be.

Two layers:
- the data: what a table of a dataset is and how it is stored (tables, parquet_layout), and an Intent checked against
  the dataset references (references);
- the code and its output: what generated code must not do (code), what an output must not be (output), and the
  primitives and tables as the Generator and the repair are told them (prompt).
"""
