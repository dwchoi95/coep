s = input()
t = "CODEFESTIVAL2016"
cnt = 0
for i, z in zip(s, t):
    if i != z:
        cnt += 1
        
print(cnt)