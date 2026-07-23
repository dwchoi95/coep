def solve():
    N, M = map(int, input().split())

    c = 0
    if M == 1:
        return c

    c += 1
    if N >= M:
        return c
    
    M -= N
    for i in range(2, 100):
        if M - N <= 0:
            return i
        M -= (N-1)

print(solve())