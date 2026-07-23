def s(x):
    print('',x,end='')
def p(u):
    if u+1:s(u);p(R[u]);p(L[u])
def i(u):
    if u+1:i(R[u]);s(u);i(L[u])
def o(u):
    if u+1:o(R[u]);o(L[u]);s(u)
        
n = int(input())
R, L = [0]*n, [0]*n
for _ in range(n):
    a, b, c = map(int, input().split())
    R[a] = b
    L[a] = c

root = (set(range(n))-set(R)-set(L)).pop()
print('Preorder');p(root)
print('\nInorder');i(root)
print('\nPostorder');o(root)
print()
     
