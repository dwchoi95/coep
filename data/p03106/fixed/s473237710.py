A, B, K=map(int, input().split())
if A>B:
    tmp=A
    A=B
    B=tmp
count=0
for i in range(A, 0, -1):
    if A%i ==0 and B%i==0:
        count+=1
    if count ==K:
        break
print(i)