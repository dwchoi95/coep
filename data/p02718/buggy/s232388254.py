x,y= list(map(int, input().split()))
i = list(map(int, input().split()))
i.sort(reverse=True)
k=sum(i)
flag=0
for j in range(y):
    if i[j]>=k/(4*(j+1)):
        flag+=1
if flag>y:
    print("No")
else:
    print("Yes")
 