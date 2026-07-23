


N,Q = map(int,input().split())
S = input()

l = [0]*N 
ans = 0

for i in range(N-1):
    if S[i] == "A" and S[i+1] == "C":
        l[i] = 1
print(l)

for i in range(Q):
    lef,rig = map(int,input().split())
    print(l[lef-1:rig-1].count(1))