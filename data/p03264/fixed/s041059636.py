import math

K = int(input())
if K % 2 == 0:
    print(int((K / 2) ** 2))
else:
    print(math.floor(K / 2) * (math.floor(K / 2) + 1))
