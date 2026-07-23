N, K = map(int, input().split())
X = list(map(int, input().split()))

answer = 10 ** 9
for i in range(N-K+1):
    b, c = X[i], X[i+K-1]
    if b * c >= 0:
        answer = min(answer, max(abs(b), abs(c)))
    else:
        d, e = min(abs(b), abs(c)), max(abs(b), abs(c))
        answer = min(answer, d*2+e)
print(answer)
