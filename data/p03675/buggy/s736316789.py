N = int(input())
s = input().split()








ans = []
if N % 2 == 1:
    for ss in s[::-1][0::2]:
        ans.append(ss[::-1])
    for ss in s[1::2]:
        ans.append(ss)
else:
    for ss in s[::-1][0::2]:
        ans.append(ss[::-1])
    for ss in s[0::2]:
        ans.append(ss)
print(" ".join(ans))
