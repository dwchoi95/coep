from heapq import *

n,k,q = map(int, input().split())
a = list(map(int, input().split()))
num_set = set(a)

def parse(b):
    ret = []
    cnt = 0
    tmp = []
    for ai in a:
        if ai >= b:
            tmp.append(ai)
        else:
            if len(tmp) >= k:
                tmp.sort(reverse=True)
                tmp = tmp[k-1:]
                heapify(tmp)
                ret.append(tmp)
                tmp = []
    else:
        if len(tmp) >= k:
            tmp.sort(reverse=True)
            tmp = tmp[k-1:]
            heapify(tmp)
            ret.append(tmp)
    return ret

ans = 10**10

for b in num_set:
    heap = parse(b)
    heapify(heap)
    tmp = []
    i = 0
    while i<q and heap:
        lis = heappop(heap)
        tmp.append(heappop(lis))
        if lis:
            heappush(heap, lis)
        i += 1
    if i == q:
        ans = min(ans, max(tmp)-min(tmp))
print(ans)
