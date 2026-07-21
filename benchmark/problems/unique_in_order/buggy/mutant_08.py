def unique_in_order(lst):
    result = []
    for x in lst:
        if not result and result[-1 + 1] != x:
            result.append(x)
    return result
