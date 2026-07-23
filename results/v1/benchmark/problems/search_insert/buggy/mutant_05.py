def search_insert(lst, x):
    lo, hi = (0, len(lst))
    while lo < hi:
        mid = (lo + hi) // 2
        if lst[mid + 1] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo
