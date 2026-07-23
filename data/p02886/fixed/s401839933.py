n = int(input())
d = list(map(int, input().split()))

i = 0
j = 0
p = 0

while i < n - 1:
    while j < n - 1:
        p += d[i] * d[j + 1]
        j = j + 1 
    i = i + 1
    j = i
print(p)