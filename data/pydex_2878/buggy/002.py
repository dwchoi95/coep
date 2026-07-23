# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
i=int(input())
t=[]
for n in range (1, i+1):
    j=input()
    s=j.split(',')
    t.append(s)
sum={}
for n in t:
    if int(n[0]) not in sum:
        sum[int(n[0])]=int(n[2])
    else:
        k=int(n[2])
        sum[int(n[0])]+=k
for n in sorted(sum):
    print(str(n)+":"+str(sum[n])