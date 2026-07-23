n=int(input())
S=list(map(int, input().split()))
Sum=sum(S)

wa=0
count=0
for i in range(n):
    if wa<Sum/2:
        wa=wa+S[i]
        count=count+1
x=int(abs(Sum-2*wa))
wa=wa-S[count-1]
        
y=int(abs(Sum-2*wa))
print(min(x,y))