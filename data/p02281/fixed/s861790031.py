from collections import defaultdict
def preorder(here, conn, chain):
    if here == -1:
        return
    chain.append(here)
    if conn[here]:
        preorder(conn[here][0], conn, chain)
        preorder(conn[here][1], conn, chain)

def inorder(here, conn, chain):
    if here == -1:
        return
    if conn[here]:
        inorder(conn[here][0], conn, chain)
        chain.append(here)
        inorder(conn[here][1], conn, chain)

def postorder(here, conn, chain):
    if here == -1:
        return
    if conn[here]:
        postorder(conn[here][0], conn, chain)
        postorder(conn[here][1], conn, chain)
    chain.append(here)

query = int(input())
connect = defaultdict(list)
in_v = [0 for n in range(query + 1)]
for _ in range(query):
    here, left, right = (int(n) for n in input().split(" "))
    connect[here] = [left, right]
    in_v[left] += 1
    in_v[right] += 1
for i in range(query):
    if not in_v[i]:
        root = i
        break
preo = []
ino = []
posto = []
preorder(root, connect, preo)
inorder(root, connect, ino)
postorder(root, connect, posto)

print("Preorder")
print("", end = " ")
print(*preo)
print("Inorder")
print("", end = " ")
print(*ino)
print("Postorder")
print("", end = " ")
print(*posto)