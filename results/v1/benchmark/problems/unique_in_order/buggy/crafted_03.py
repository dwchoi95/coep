def unique_in_order(lst):
    result = []
    for i in range(len(lst) - 1):
        if lst[i] != lst[i + 1]:
            result.append(lst[i])
    return result
