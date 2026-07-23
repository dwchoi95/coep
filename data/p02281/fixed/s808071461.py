class NullNode():
    def __init__(self):
        self.id = -1

class Node():
    def __init__(self, id):
        self.id = id
        self.parent = NullNode()
        self.left = NullNode()
        self.right = NullNode()

def preorder(node, out_list=[]):
    if node.id != -1:
        out_list.append(str(node.id))
        out_list = preorder(node.left, out_list)
        out_list = preorder(node.right, out_list)
    return out_list

def inorder(node, out_list=[]):
    if node.id != -1:
        out_list = inorder(node.left, out_list)
        out_list.append(str(node.id))
        out_list = inorder(node.right, out_list)
    return out_list

def postorder(node, out_list=[]):
    if node.id != -1:
        out_list = postorder(node.left, out_list)
        out_list = postorder(node.right, out_list)
        out_list.append(str(node.id))
    return out_list

n = int(input())
node_list = [Node(id) for id in range(n)]
for i in range(n):
    [id, left, right] = [int(j) for j in input().split()]
    i_node = node_list[id]
    if left != -1:
        i_node.left = node_list[left]
        node_list[left].parent = node_list[id]
    if right != -1:
        i_node.right = node_list[right]
        node_list[right].parent = node_list[id]

for node in node_list:
    if node.parent.id == -1:
        root = node

print('Preorder')
out_list = preorder(root)
print(' ' + ' '.join(out_list))

print('Inorder')
out_list = inorder(root)
print(' ' + ' '.join(out_list))

print('Postorder')
out_list = postorder(root)
print(' ' + ' '.join(out_list))

