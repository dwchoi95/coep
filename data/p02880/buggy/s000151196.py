N = input()

hoge = []
for i in range(1, 10):
    for j in range(1, 10):
        hoge.append(i * j)

if N in hoge:
    print("Yes")
else:
    print("No")