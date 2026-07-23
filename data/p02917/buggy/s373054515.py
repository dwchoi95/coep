n = int(input())
b_list = [int(i) for i in input().split()]
a_list = [0] * n
before_val = 0
for i in range(n-1):
    target = b_list[i]
    if a_list[i] == before_val:
        a_list[i], a_list[i+1] = b_list[i], b_list[i]
    else:
        a_list[i+1] = b_list[i]
print(sum(a_list))