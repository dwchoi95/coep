a,b = map(int,input().split(" "))
k = 0
while ((a-1) * k + 1) < b:
    k +=1
print(k)