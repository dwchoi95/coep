import heapq

def top_k(lst, k):
    return heapq.nsmallest(k, lst)
