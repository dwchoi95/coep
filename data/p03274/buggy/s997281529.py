N, K = map(int, input().split())
X = list(map(int, input().split()))

answer = 10 ** 9
for i in range(N-K+1):
    b, c = X[i], X[i+K-1]
    if b * c >= 0:
        answer = min(answer, max(abs(b), abs(c)))
    else:
        answer = min(answer, abs(b)*2+abs(c))
print(answer)