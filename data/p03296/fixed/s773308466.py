n=int(input())
a=[int(i)for i in input().split()]

count=0
p=1
while p<n:
    if a[p-1] == a[p]:
        try:
         if a[p-1] == a[p] == a[p+1]:
             a[p]=a[p-1]+a[p]+a[p+1]
             p+=1
             count+=1
         else:
             a[p]=a[p-1]+a[p]+a[p+1]
             p+=1
             count+=1
        except:
            if a[p-1]==a[p]:
                p+=1
                count+=1
    p+=1
print(count)
