def search_insert(lst, x):
    for i, v in enumerate(lst):
        if v >= x:
            return i + 1
    return len(lst)
