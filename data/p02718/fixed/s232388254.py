x,y= list(map(int, input().split()))
i = list(map(int, input().split()))
i.sort(reverse=True)
k=sum(i)
flag=0
if i[y-1]>=k/(4*y):
    print("Yes")
else:
    print("No")