n = int(input())
b = list(map(int, input().split()))

sum = b[0]*2
if n >= 4:
    for i in range(n-2):
        if b[i] > b[i+1]:
            b[i] = b[i+1]
        sum += b[i]

sum += b[-1]
print(sum)
