N,M = map(int, input().split())
import heapq
A = list(map(int, input().split()))
A = [(-x,x) for x in A]
heapq.heapify(A)
def conf(A, M):
    if M > 0:
        a = heapq.heappop(A)[1]
        heapq.heappush(A, (-int(a/2), int(a/2)))
    else:
        return A
    return conf(A, M-1)
B = [a[1] for a in A]
print(sum(B))