def unique_in_order(lst):
    result = []
    prev = None
    for x in lst:
        if x != prev:
            result.append(x)
    return result
