K=int(input())
if K%2==0:
    m=(K/2)**2
else:
    m=((K-1)/2)*(((K-1)/2)+1)
n=int(m)
print(n)
