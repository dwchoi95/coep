n = int(input())
a = list(map(int,input().split()))
b = list(map(int,input().split()))


c = []
count = 0

for i in range(n):

    if a[i] - b[i] >= 0:
        count += b[i]
    elif a[i] - b[i] < 0:
        count += a[i]
        if a[i+1] + (a[i] - b[i]) >0:
            a[i+1] = a[i+1] + (a[i] - b[i])
            count += (a[i]-b[i])
        elif a[i+1] + (a[i]-b[i]) <=0:
            count += a[i+1]
            a[i+1] = 0
            
print(count)