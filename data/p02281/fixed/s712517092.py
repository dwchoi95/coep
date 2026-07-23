
class Tree:
    def __init__(self,parent,left,right):
        self.parent = parent
        self.left = left
        self.right = right


def preparse(u):
    if u == -1: return
    print(" ", end="")
    print(u, end="")
    preparse(trees[u].left)
    preparse(trees[u].right)


def inparse(u):
    if u == -1: return
    
    inparse(trees[u].left)
    
    print(" ", end="")
    print(u, end="")
    
    inparse(trees[u].right)
    

def postparse(u):
    if u == -1: return
    
    postparse(trees[u].left)
    
    postparse(trees[u].right)
    
    print(" ", end="")
    print(u, end="")


N = int(input())

trees = [Tree(-1,-1,-1) for i in range(N)]
for i in range(N):
    l = list(map(int, input().split()))
    no = l[0]
    left = l[1]
    right = l[2]
    trees[no].left = left
    trees[no].right = right
    if left != -1: trees[left].parent = no
    if right != -1: trees[right].parent = no

r = 0
for i in range(N):
    if trees[i].parent == -1:
        r = i

print("Preorder")
preparse(r)
print("")
print("Inorder")
inparse(r)
print("")
print("Postorder")
postparse(r)
print("")