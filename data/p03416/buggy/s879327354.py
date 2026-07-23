a, b =map(int, input().split())
count=0
for i in range(a,b):
    m = list(str(i))
    if m[0]==m[3]:
        if m[1]==m[2]:
            count+=1
print(count)