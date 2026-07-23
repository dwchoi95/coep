a, b, k = map(int, input().split())
l = []

for i in range((min(a,b))):
    if a%(i+1)==0 and b%(i+1)==0:
        l.append(i+1)

print(l[k-1])