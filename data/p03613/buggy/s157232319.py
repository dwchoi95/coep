n = int(input())
k = [0] * 100001
for a in map(int, input().split()):
    k[a] += 1
print(max(map(sum, zip(k[1:], k[2:], k[3:]))))
