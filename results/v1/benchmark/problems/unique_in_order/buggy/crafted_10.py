def unique_in_order(lst):
    result = []
    for x in lst:
        if not result or result[0] != x:
            result.insert(0, x)
    return result
