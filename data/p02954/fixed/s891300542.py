s = input()
n = len(s)

def solve(s, c1, c2):
    res = [0] * (n)
    odd = 0
    even = 0
    for i in range(n):
        if s[i] == c1:
            if i % 2 == 1:
                odd += 1
            else:
                even += 1
        if s[i] == c2:
            if i % 2 == 1:
                res[i] += odd
                res[i-1] += even
            else:
                res[i] += even
                res[i-1] += odd
            odd, even = 0, 0
    return res

A = solve(s, 'R', 'L')
B = solve(s[::-1], 'L', 'R')[::-1]
ans = [a+b for a, b in zip(A,B)]
print(' '.join(map(str, ans)))