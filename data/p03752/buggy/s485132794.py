from itertools import combinations

N, K = map(int, input().split())
A = list(map(int, input().split()))

best_score = float("inf")
for sel in combinations(range(N), K):
    cost = 0

    
    
    first = sel[0]
    first_max = A[first]
    for k in range(first):
        first_max = max(first_max, A[k])
    current = first_max
    if first_max > 0:
        cost += abs(A[first] - current) 
    
    for i in range(1, K):
        if current > A[sel[i]]:
            cost += abs(A[sel[i]] - current) + 1
            current += 1
        else:
            current = A[sel[i]] + 1
    
    best_score = min(best_score, cost)
print(best_score)