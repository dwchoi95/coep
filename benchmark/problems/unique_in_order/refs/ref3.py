def unique_in_order(lst):
    from itertools import groupby
    return [key for key, _ in groupby(lst)]
