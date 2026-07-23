s=input()
l=int(input())
x=''
for i in range(len(s)):
        if i%l==0:
                x+=s[i]
print(x)
