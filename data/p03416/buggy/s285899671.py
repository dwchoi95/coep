a,b = map(int,(input().split()))
count = 0
for i in range(a,b+1):
    num_str = str(i)
    if (num_str[0] == num_str[4]) and (num_str[1] == num_str[3]):
        count += 1
print(range(a,b))