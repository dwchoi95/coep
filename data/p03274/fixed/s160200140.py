
import bisect 
n,k = map(int,input().split())
x = list(map(int,input().split()))

w  = x.count(0)
for i in range(w):
    x.remove(0)

if k <= w:
    print(0)
else:
    k = k -w
    

    r = bisect.bisect_left(x,0)
    
    if x[-1]<0:
        print(abs(x[len(x)-k]))
    elif x[0] > 0:
        print(x[k-1])    
    else:
        ass = 10 ** 10
        ans = 10**10
        for i in range(r,min(len(x),r + k )):
            if i-r+1 >= k:
                ans = abs(x[i])
            
            else:
                if i - k + 1 >= 0:
                    ans = x[i] + abs(x[i-k+1]) + min(x[i],abs(x[i-k+1]))
            ass = min(ass,ans)
        if r-k >= 0:
            ans = abs(x[r-k])
        ass = min(ass,ans)
        print(ass)