s = input()
t = input()

def z_algorithm(s):
    a = [0] * len(s)
    i = 1
    j = 0
    a[0] = len(s)
    while i < len(s):
        while i + j < len(s) and s[j] == s[i+j]:
            j += 1
        a[i] = j
        if j == 0:
            i += 1
            continue
        k = 1
        while i + k < len(s) and k + a[k] < j:
            a[i+k] = a[k]
            k += 1
        i += k
        j -= k
    return a

def solve(i, li):
    ans = 0
    while True:
        if i < 0 or len(li) <= i or visited[i]:
            break
        if li[i] < len(t):
            visited[i] = True
            break
        if li[i] >= len(t):
            visited[i] = True
            ans += 1
            i += len(t)
    return ans


new_s = ""
while True:
    new_s += s
    if len(new_s) > len(t):
        s = new_s
        break

s = s
li = z_algorithm(t + s)[len(t):]
visited = [False] * len(li)
ans1 = 0
for i in range(len(li)):
    ans1 = max(ans1, solve(i, li))

print(ans1)