n = int(input())
b_list = [int(i) for i in input().split()]
a_list = [0] * n
before_val = 0
for i in range(n-1):
    target = b_list[i]
    if i == 0:
        a_list[i], a_list[i+1] = target, target
    elif before_val >= target:
        a_list[i], a_list[i+1] = target, target
    else:
        a_list[i], a_list[i+1] = before_val, target
    before_val = target
print(sum(a_list))