N = int(input())
B = list(map(int, input().split()))

sum = 0
if N==2:
    sum += B[0]*2
else:
    sum += min([B[0], B[1]])
    for i in range(N-2):
        sum += min([B[i], B[i+1]])
    sum += B[N-2]

print(sum)