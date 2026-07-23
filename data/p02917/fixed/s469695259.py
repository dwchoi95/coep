N = int(input())
Bi = list(map(int, input().split()))
listA = [0 for i in range(N)]
listA[N-1] = Bi[N-2]
gokei = 0
listA[0] = Bi[0]
for j in range(N-2, 0, -1):
    listA[j] = min(Bi[j], Bi[j-1])

for k in listA:
    gokei += k
print(gokei)