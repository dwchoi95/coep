def unique_in_order(lst):
    result = []
    for x in lst:
        if x not in result:
            result.append(x)
    return result
