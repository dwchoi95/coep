def unique_in_order(lst):
    for x in lst:
        if lst.count(x) > 1:
            lst.remove(x)
    return lst
