n = int(input())
for i in range(1, 10):
    for j in range(1, 10):
        print(i,j)
        if i * j == n:
            print('Yes')
            exit()
else:print('No')