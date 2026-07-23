a =int(input())
b =list(map(int,input().split()))
x=0
for i in range(a-1):
	if b[i]==b[i+1]:
		b[i+1]=11111
		x=x+1
print(x)