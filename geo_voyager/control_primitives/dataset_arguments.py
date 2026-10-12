def dataset_arguments(args: tuple, dataset_id: str, minimum: int) -> tuple:
    """The arguments after the Dataset id, which a call may write first or leave out.

    A primitive reads one Dataset, so the id says nothing new: load_stations(connection) and the older
    load_stations('yuiseki/ekidata-jp', connection) both work. Another Dataset's id fails before anything is read.
    """
    if args and isinstance(args[0], str):
        if args[0] != dataset_id:
            raise ValueError(f'This primitive reads only {dataset_id}, not {args[0]}')
        args = args[1:]
    if len(args) < minimum:
        raise TypeError(f'Expected {minimum} arguments after the Dataset id, got {len(args)}')
    return args
