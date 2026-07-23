n = int(input())
a_l = list(map(int,input().split()))

if a_l[0] != 0:
    if n == 0:
        print(1)
    else:
        print(-1)
    exit()

tree = [0]*(n+1)
tree[0] = 1
for i in range(1,n+1):
    tree[i] = (tree[i-1] - a_l[i-1]) * 2


if tree[-1] < a_l[-1]:
    print(-1)
    exit()

while tree[-1] != a_l[-1]:
    tree[-1] -= 1
    i = 1
    while True:
        i += 1 
        if tree[-(i-1)] >= (tree[-i] - a_l[-i]):
            break
        tree[-i] -= 1


ans = 0
for val in tree:
    ans += val
print(ans)