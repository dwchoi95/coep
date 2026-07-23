n,k = map(int,input().split())
a = [int(x) for x in input().split()]
_min = 1145141919810
for i in range(2**(n-1)):
    ctr = 0
    val = 0
    flag = 0
    h_max = a[0]
    for j in range(n-1):
        if (i>>j)&1:
            ctr+=1
            h_max = h_max+1 if h_max>=a[j+1] else a[j+1]
            val+=h_max-a[j+1]
            if ctr>=k-1:
                flag=1
                break
    if val<_min and flag and h_max<=10**9:
        _min = val
print(_min)