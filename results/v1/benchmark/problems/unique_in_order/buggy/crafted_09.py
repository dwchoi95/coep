def unique_in_order(lst):
    result = []
    for i in range(1, len(lst)):
        if lst[i] == lst[i - 1]:
            continue
        result.append(lst[i])
    return result
