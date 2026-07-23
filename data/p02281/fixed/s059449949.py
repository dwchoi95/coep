n = int(input())
root = set(range(n))
nodes = [0 for i in range(n)]
for i in range(n):
    node = list(map(int, input().split()))
    children = node[1:3]
    root -= set(children)
    nodes[node[0]] = children

def preorder(id):
    if(id == -1):
        return
    order.append(id)
    preorder(nodes[id][0])
    preorder(nodes[id][1])

def inorder(id):
    if(id == -1):
        return
    inorder(nodes[id][0])
    order.append(id)
    inorder(nodes[id][1])

def postorder(id):
    if(id == -1):
        return
    postorder(nodes[id][0])
    postorder(nodes[id][1])
    order.append(id)

order = []
preorder(list(root)[0])
print('Preorder')
print(' ', end='')
print(*order)
order = []
inorder(list(root)[0])
print('Inorder')
print(' ', end='')
print(*order)
order = []
postorder(list(root)[0])
print('Postorder')
print(' ', end='')
print(*order)

