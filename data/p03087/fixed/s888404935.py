n,q = map(int,input().split())
S = input()
tb = [0 for i in range(n)]
for i in range(1,n):
    if S[i]=='C' and S[i-1]=='A':
        tb[i] = tb[i-1]+1
    else:
        tb[i] = tb[i-1]
for i in range(q):
    l,r = map(int,input().split())
    print(tb[r-1]-tb[l-1])

