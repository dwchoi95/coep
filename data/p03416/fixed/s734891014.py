a, b =map(int, input().split())
count=0
for i in range(a,b+1):
    m = list(str(i))
    if m[0]==m[4]:
        if m[1]==m[3]:
            count+=1
print(count)