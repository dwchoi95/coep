N , M = input().split()
array = input().split()
flag = 0

N = int(N)
M = int(M)

iarray = []

for i in array:
    iarray.append(int(i))

total = sum(iarray)

for i in iarray:
    if i >= total/(4*M):
        flag += 1
if flag >= M:
    print("Yes")
else:
    print("No")