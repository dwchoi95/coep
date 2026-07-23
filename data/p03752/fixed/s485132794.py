from itertools import combinations

N, K = map(int, input().split())
A = list(map(int, input().split()))














    










best_score = float("inf")
for sel in combinations(range(N), K):
    sel = sorted(sel)
    cost = 0
    m = -1

    for i in range(N):
        if i not in sel:
            
            m = max(m, A[i])
        else:
            if m >= A[i]:
                cost += 1 + m - A[i]
                m += 1
            else:
                m = A[i]
    best_score = min(best_score, cost)
print(best_score)