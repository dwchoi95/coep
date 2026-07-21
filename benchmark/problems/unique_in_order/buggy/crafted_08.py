def unique_in_order(lst):
    if not lst:
        return []
    result = [lst[0]]
    for x in lst:
        if x != lst[0]:
            result.append(x)
    return result
