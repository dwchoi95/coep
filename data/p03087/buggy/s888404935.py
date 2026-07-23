n,q = map(int,input().split())
S = input()
tb = [0 for i in range(n)]
for i in range(n):
    if i==0 or S[i]!='C':
        tb[i] = tb[i-1]
        continue
    print(S[i])
    if S[i-1]=='A':
        tb[i] = tb[i-1]+1
for i in range(q):
    l,r = map(int,input().split())
    print(tb[r-1]-tb[l-1])
