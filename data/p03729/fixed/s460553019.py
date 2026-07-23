Nstr = input().split()
result = 'YES'
for i in range(2):
    if Nstr[i][-1] != Nstr[i + 1][0]:
        result = 'NO'
print(result)