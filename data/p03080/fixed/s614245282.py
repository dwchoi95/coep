A = int(input())
B = list(input())

count_RED = 0
for i in range (0, A):
    if B[i] == "R":
        count_RED += 1
count_BLUE = A - count_RED
if (count_RED > count_BLUE):
    print('Yes')
else:
    print('No')    