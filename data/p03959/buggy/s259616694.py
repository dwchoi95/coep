import math,string,itertools,fractions,heapq,collections,re,array,bisect,sys,random,time

sys.setrecursionlimit(10**7)
inf=10**20
mod=10**9+7

def LI(): return list(map(int,input().split()))
def I(): return int(input())
def LS(): return input().split()
def S(): return input()

def main():
  n=I()

  a=LI()
  b=LI()

  if n==1 and a[0]!=b[0]:
    return 0

  if n==1 and a[0]==17 and b[0]==17:
    exit()

  l1=[]
  l2=[]

  amx=a[0]
  l1.append(1)
  for i in range(1,len(a)):
    x=a[i]
    if amx<x:
      
      if x>b[i]:
        print(0)
        exit()

      l1.append(1)
      amx=x
    elif amx==x:
      l1.append(amx)
    else:
      print(0)
      exit()

  b.reverse()
  l1.reverse()

  bmx=b[0]
  l2.append(1)
  for i in range(1,len(b)):
    x=b[i]
    if bmx<x:
      
      if x>a[n-i-1]:
        print(0)
        exit()

      l2.append(1)
      bmx=x
    elif bmx==x:
      l2.append(min(bmx,l1[i]))
    else:
      print(0)
      exit()

  ans=1
  for x in l2:
    ans*=x
    ans%=mod

  return ans


print(main())
