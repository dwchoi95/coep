a, b, c = input().split()
result = 'NO'
if a[-1] == b[0]:
    if b[-1] == c[0]:
        result = 'YES'
print(result)