a,b = map(int,input().split(" "))
k = 1
while (a * k + 1) < b:
    k +=1
print(k)