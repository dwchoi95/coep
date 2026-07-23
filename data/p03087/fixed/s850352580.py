N, Q = map(int, input().split())
S = input()
flag = True
R = [0]*N
a = 0
for i in range(N):
    s = S[i]
    if s == "A":
        flag = True
    elif s == "C" and flag:
        a += 1
        flag = False
    else:
        flag = False
    R[i] = a
for i in range(Q):
    l, r = map(int, input().split())
    print(R[r-1] - R[l-1])
