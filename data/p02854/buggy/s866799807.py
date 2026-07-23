n=int(input())
S=list(map(int, input().split()))
Sum=sum(S)

wa=0
count=0
for i in range(n):
    if wa<Sum/2:
        wa=wa+S[i]
        count=count+1
if count==n:
    wa=wa-S[n-1]
        
print(int(abs(Sum-2*wa)))