n = int(input())
tree = [[] for i in range(n)]
for i in range(n):
    id, left, right = map(int, input().split())
    tree[id] = [left, right]

def preoder(id):
    if id == -1:
        return
    print(' ' + str(id), end='')
    preoder(tree[id][0])
    preoder(tree[id][1])

def inorder(id):
    if id == -1:
        return
    inorder(tree[id][0])
    print(' ' + str(id), end='')
    inorder(tree[id][1])

def postorder(id):
    if id == -1:
        return
    postorder(tree[id][0])
    postorder(tree[id][1])
    print(' ' + str(id), end='')

print('Preoder')
preoder(0)
print('')
print('Inorder')
inorder(0)
print('')
print('Postorder')
postorder(0)

