def search_insert(lst, x):
    for i, v in enumerate(lst):
        if v >= x:
            return i
    return len(lst)
