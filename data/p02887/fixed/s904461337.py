N = int(input())
s= list(input())

s0 = s.pop()

cnt = 1

while s:
    s1 = s.pop()
    if s1!=s0:
        cnt += 1
        s0 = s1
print(cnt)
