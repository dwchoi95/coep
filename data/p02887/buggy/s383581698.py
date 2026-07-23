n=int(input())
s=input()
k=0
l=set(s)
if len(l)==1:
    print(len(l))
    exit()
for i in range(n-1):
    if s[i]==s[i+1]:
        k+=1
print(k)