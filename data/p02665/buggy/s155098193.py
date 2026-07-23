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


tree[-1] = a_l[-1]
for i in range(2,n+2):
    
    if tree[-i] == tree[-(i-1)] + a_l[-i]:
        break
    else:
        tree[-i] = min(tree[-i], tree[-(i-1)] + a_l[-i])
    












ans = 0
for val in tree:
    ans += val
print(ans)