import sys
n=int(input())
for i in range(1,10):
    if n%i==0:
        print("Yes")
        sys.exit()
print("No")