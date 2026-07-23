def top_k(lst, k):
    temp = list(lst)
    result = []
    for _ in range(k):
        m = max(temp)
        temp.remove(m)
        result.append(m)
    return result
