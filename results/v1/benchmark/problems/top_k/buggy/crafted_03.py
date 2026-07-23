def top_k(lst, k):
    uniq = sorted(set(lst), reverse=True)
    return uniq[:k]
