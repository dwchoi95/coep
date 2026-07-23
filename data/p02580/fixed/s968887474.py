import math,itertools,fractions,heapq,collections,bisect,sys,queue,copy

sys.setrecursionlimit(10**7)
inf=10**20
mod=10**9+7
dd=[(-1,0),(0,1),(1,0),(0,-1)]
ddn=[(-1,0),(-1,1),(0,1),(1,1),(1,0),(1,-1),(0,-1),(-1,-1)]

def LI(): return [int(x) for x in sys.stdin.readline().split()]

def I(): return int(sys.stdin.readline())
def F(): return float(sys.stdin.readline())
def LS(): return sys.stdin.readline().split()
def S(): return input()

def main():
  H,W,M=LI()
  h=[0]*H
  w=[0]*W
  d={}
  for _ in range(M):
    a,b=LI()
    a-=1
    b-=1
    h[a]+=1
    w[b]+=1
    d[(a,b)]=1

  h_koho=[]
  w_koho=[]

  h_max=max(h)
  w_max=max(w)

  for i,x in enumerate(h):
    if x==h_max:
      h_koho.append(i)
  for i,x in enumerate(w):
    if x==w_max:
      w_koho.append(i)

  for x in h_koho:
    for y in w_koho:
      if (x,y) not in d:
        return h_max+w_max

  return h_max+w_max-1


print(main())
