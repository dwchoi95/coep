X,Y,Z,K = map(int,input().split())
A = list(map(int,input().split()))
B = list(map(int,input().split()))
C = list(map(int,input().split()))

AB = []
for a in A:
    for b in B:
        AB.append(a+b)
AB.sort(reverse=True)

AB = AB[:K]
C.sort(reverse=True)
ABC = []
i = 0
for ab in AB:
    if i >= K: break
    for c in C:
        ABC.append(ab+c)
        i += 1

ABC.sort(reverse=True)

for i in range(K): print(ABC[i])