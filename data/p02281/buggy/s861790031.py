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
for _ in range(query):
    here, left, right = (int(n) for n in input().split(" "))
    connect[here] = [left, right]
preo = []
ino = []
posto = []
preorder(0, connect, preo)
inorder(0, connect, ino)
postorder(0, connect, posto)

print("Preorder")
print(*preo)
print("Inorder")
print(*ino)
print("Postorder")
print(*posto)