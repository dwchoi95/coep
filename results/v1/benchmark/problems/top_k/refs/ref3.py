import heapq

def top_k(lst, k):
    return heapq.nlargest(k, lst)
