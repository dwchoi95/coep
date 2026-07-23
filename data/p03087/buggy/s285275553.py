N, Q = map(int, input().split())
S=list(input())
list=[]
for i in range(0, N-1):
    if S[i] == "A" and S[i+1] == "C":
        list.append(i)
count=0
for i in range(Q):
    l, r = map(int, input().split())
    for j in list:
        if l-1 <= j < r-1:
            count+=1
        else:
            count+=0
    print(count)