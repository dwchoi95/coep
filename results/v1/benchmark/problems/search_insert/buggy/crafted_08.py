def search_insert(lst, x):
    for i in range(len(lst) - 1, -1, -1):
        if lst[i] < x:
            return i
    return 0
