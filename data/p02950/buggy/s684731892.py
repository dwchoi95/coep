p = int(input())
b_list = [0 for _ in range(p)]
a_list = list(map(int,input().split()))
if a_list[0] == 1:
    a_list[0] = 0
    b_list[0] = 1
    b_list[p-1] = -1
c = 0
for i in a_list:
    if i == 1:
        for j in range(p-1):
            b_list[j+1] -= (c**(p-j-1))%p
    c += 1
for j in b_list:
    print(j % p,end = ' ')
