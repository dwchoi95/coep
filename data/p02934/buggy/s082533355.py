N = int(input())
A = [int(s) for s in input().split(' ')]

ret = 1
for a in A:
    ret *= a

print(ret / sum(A))

