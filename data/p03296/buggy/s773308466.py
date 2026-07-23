n=int(input())
a=[int(i)for i in input().split()]

count=0
p=1
while p<n-1:
    if a[p-1] == a[p]:
        if a[p-1] == a[p] == a[p+1]:
            a[p]=a[p-1]+a[p]+a[p+1]
            p+=2
            count+=1
        else:
            a[p]=a[p-1]+a[p]+a[p+1]
            p+=2
            count+=1
    else:
        p+=1
print(count)
