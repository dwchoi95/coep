a,b,c=map(int,input().split())
if a+b==c:
    print("Yes")
    exit()
if b+c==a:
    print("Yes")
    exit()
if a+c==b:
    print("Yes")
    exit()
print("No")
