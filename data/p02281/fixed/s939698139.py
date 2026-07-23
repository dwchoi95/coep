
N = int(input())
T = []
class Tree:
    def __init__(self,ID,l=None,r=None,p=-1):
        self.ID = ID
        self.l = l
        self.r = r
        self.p = p

    def makeTree(self):
        for i in range(N):
            T.append(Tree(i))


def preParse(tree):
    if tree == None:
        return
    else:
        ID = tree.ID
        global preList
        preList.append(ID)
        preParse(tree.l)
        preParse(tree.r)
        
def inParse(tree):
    if tree == None:
        return
    else:
        ID = tree.ID
        global inList
        inParse(tree.l)
        inList.append(ID)
        inParse(tree.r)

def posParse(tree):
    if tree == None:
        return
    else:
        ID = tree.ID
        global posList
        posParse(tree.l)
        posParse(tree.r)
        posList.append(ID)
        
    
trees = [list(map(int,input().split())) for i in range(N)]
Tree.makeTree(Tree)
for i in range(N):
    ID,l,r = trees[i]
    tree = T[ID]
    if l != -1:
        T[l].p = tree
        tree.l = T[l]
    if r != -1:
        T[r].p = tree
        tree.r = T[r]
    
for i in range(N):
    if T[i].p == -1:
        parent = T[i]

preList = []
inList = []
posList = []
preParse(parent)
inParse(parent)
posParse(parent)

def convert(List, order):
    a =  " " + " ".join([str(num) for num in List])
    print("{}".format(order))
    print(a)
convert(preList, "Preorder")
convert(inList, "Inorder")
convert(posList, "Postorder")

