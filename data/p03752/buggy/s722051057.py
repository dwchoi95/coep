N,K=list(map(int,input().split()))
height=list(map(int,input().split()))
ans=10**10
count=0
for x in range(1, N):
    if height[0] < height[x]:
        count += 1
if count>=K:
    print(0)
    exit()
for i in range(2**N):
    cost=0
    height2=height.copy()
    for j in range(N):
        if i>>j&1:
            count=0
            for k in range(j):
                if height2[k]>=height2[j]:
                    cost+=height2[k]-height2[j]+1
                    height2[j]+=height2[k]-height2[j]+1
            for x in range(1,N):
                if height2[0]<height2[x]:
                    count+=1

            if ans>cost and count==K-1:
                ans=cost


print(ans)