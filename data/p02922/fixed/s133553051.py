def solve():
    N, M = map(int, input().split())

    if M == 1:
        return 0
    
    
    diff = N-1
    sum = N
    c = 1
    while sum < M:
        sum += diff
        c += 1
    return c

print(solve())