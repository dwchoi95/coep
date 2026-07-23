def LI(): return list(map(int,input().split()))
N,K = LI()
a = LI()
ans = float('INF')
for i in range(2**(N-1)):
    bit = [i>>j&1 for j in range(N-1)]
    if K-1!=bit.count(1):
        continue
    NO_bit1 = [k for k in range(N-1) if bit[k]==1]
    temp = 0
    for l,x in enumerate(NO_bit1,1):
        if a[x+1]>=a[0]+l:
            continue
        temp += (a[0]+l)-a[x+1]
    ans = min(ans,temp)
print(ans)
