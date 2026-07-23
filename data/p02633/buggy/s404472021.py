

X = int(input())

index = 1
while True:
    if X * index % 180 == 0:
        print(index*2)
        break
    index += 1
