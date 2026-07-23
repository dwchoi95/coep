hw = list(map(int, input().split()))

if hw[0] % 2 == 0 and hw[1] % 2 == 0:
    count = hw[0] * hw[1] 
elif hw[0] % 2 != 0 and hw[1] % 2 == 0:
    count = (hw[0] + 1) * hw[1] 
elif hw[0] % 2 == 0 and hw[1] % 2 != 0:
    count = (hw[1] + 1) * hw[0] 
else:
    count = (hw[0] + 1) * (hw[1] + 1) 
print(count)
