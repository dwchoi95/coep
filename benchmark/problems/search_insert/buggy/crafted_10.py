def search_insert(lst, x):
    count = 0
    for v in lst:
        if v <= x:
            count += 1
    return count
