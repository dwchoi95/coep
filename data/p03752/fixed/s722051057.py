N, K = list(map(int, input().split()))
height = list(map(int, input().split()))
ans = 10 ** 10
if N==K:
    cost=0
    for i in range(1,N):
        if height[i-1]>=height[i]:
            cost+=height[i-1]-height[i]+1
            height[i]+=height[i-1]-height[i]+1
    print(cost)
    exit()
for i in range(2 ** N):
    count=1
    cost = 0
    height2 = height.copy()
    for j in range(N):
        if i >> j & 1:
            if j!=0:
                tarou=max(height2[:j])
                if height2[j]<=tarou:
                    cost+=tarou-height2[j]+1
                    height2[j]+=tarou-height2[j]+1
                    count+=1
                else:count+=1
    
    
    
    
    
    if ans > cost and count >= K:
        ans = cost

print(ans)