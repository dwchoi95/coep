n = int(input())
tree = [[-1, -1, True] for i in range(n)]
for i in range(n):
    id, left, right = map(int, input().split())
    if left != -1:
        tree[id][0] = left
        tree[left][2] = False
    if right != -1:
        tree[id][1] = right
        tree[right][2] = False

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

root = 0
for i, node in enumerate(tree):
    if node[2] == True:
        root = i

print('Preorder')
preoder(root)
print('')
print('Inorder')
inorder(root)
print('')
print('Postorder')
postorder(root)
print('')

