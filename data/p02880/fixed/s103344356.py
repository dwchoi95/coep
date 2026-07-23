N=int(input())
for a in range(1,10):
    for b in range(1,10):
        if a*b==N:
            print("Yes")
            exit()
print("No")