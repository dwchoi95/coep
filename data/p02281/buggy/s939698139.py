
N = int(input())
T = [None for i in range(N)]
class Tree:
    def __init__(self, ID,p=-1):
        self.ID = ID

    def makeTree(self, tree):
        ID = tree.ID
        if ID == -1:
            return
        else:
            for i in range(N):
                if trees[i][0] == ID:
                    [ID,l,r] = trees[i]
                    tree.l = Tree(l)
                    tree.r = Tree(r)
                    treeL = tree.l
                    treeR = tree.r
                    treeL.p = tree
                    treeR.p = tree

                    self.makeTree(self,treeL)
                    self.makeTree(self,treeR)

def preParse(tree):
    ID = tree.ID
    if ID == -1:
        return
    else:
        global preList
        preList.append(ID)
        treeL = tree.l
        treeR = tree.r
        preParse(treeL)
        preParse(treeR)
        
def inParse(tree):
    ID = tree.ID
    if ID == -1:
        return
    else:
        global inList
        treeL = tree.l
        treeR = tree.r
        inParse(treeL)
        inList.append(ID)
        inParse(treeR)

def posParse(tree):
    ID = tree.ID
    if ID == -1:
        return
    else:
        global posList
        treeL = tree.l
        treeR = tree.r
        posParse(treeL)
        posParse(treeR)
        posList.append(ID)
        
    
trees = [list(map(int,input().split())) for i in range(N)]
ID = trees[0][0]
tree = Tree(ID)
Tree.makeTree(Tree,tree)

preList = []
inList = []
posList = []
preParse(tree)
inParse(tree)
posParse(tree)

def convert(List, order):
    a =  " " + " ".join([str(num) for num in List])
    print("{}".format(order))
    print(a)
convert(preList, "Preorder")
convert(inList, "Inorder")
convert(posList, "Postorder")
