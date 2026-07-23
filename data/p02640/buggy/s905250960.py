x,y=map(int,input().split())
for i in range(100):
    if i*2+(x-i)*4==y:
        print("Yes")
        break
else:
    print("No")