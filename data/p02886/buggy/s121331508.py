import copy
x = input()
y = list(map(int,input().split()))

result = 0
for i, j in enumerate(y):
    if i == (len(y) - 1):
        break
    array = copy.deepcopy(y)
    b = array.pop(i)
    a_sum = sum(array)
    result = result + b * len(y) + a_sum

print(result)
