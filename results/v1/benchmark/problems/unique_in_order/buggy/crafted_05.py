def unique_in_order(lst):
    result = []
    prev = 0
    for x in lst:
        if x != prev:
            result.append(x)
        prev = x
    return result
