n = int(input())

L = set()
for i in range(1,10):
    for j in range(1,10):
        result = i*j
        L.add(result)
if n in L:
    print("Yes")
elif n not in L:
    print("No")