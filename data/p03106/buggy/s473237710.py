A, B, K=map(int, input().split())
if A>B:
    tmp=A
    A=B
    B=tmp
count=0
for i in range(1,A+1):
    if A%i ==0 & B%i==0:
        count+=1
    if count ==K:
        break
print(i)