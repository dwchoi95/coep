def unique_in_order(lst):
    result = []
    for x in lst:
        if not result or result[-1 + 1] != x:
            result.append(x)
    return result
