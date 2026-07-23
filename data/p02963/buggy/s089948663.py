import sys,collections as cl,bisect as bs
sys.setrecursionlimit(100000)
input = sys.stdin.readline
mod = 10**9+7
Max = sys.maxsize
def l(): 
  return list(map(int,input().split()))
def m(): 
  return map(int,input().split())
def onem(): 
  return int(input())
def s(x): 
  a = []
  if len(x) == 0:
    return []
  aa = x[0]
  su = 1
  for i in range(len(x)-1):
    if aa != x[i+1]:
      a.append([aa,su])
      aa = x[i+1]
      su = 1
    else:
      su += 1
  a.append([aa,su])
  return a
def jo(x): 
  return " ".join(map(str,x))
def max2(x): 
  return max(map(max,x))
def In(x,a): 
    k = bs.bisect_left(a,x)
    if k != len(a) and a[k] ==  x:
        return True
    else:
        return False

def pow_k(x, n):
    ans = 1
    while n:
        if n % 2:
            ans *= x
        x *= x
        n >>= 1
    return ans



s = onem()

x = [0,10**9,0]
y = [0,1,0]

x[-1] = s % 10**9
y[-1] = s 

print(x[0],y[0],x[1],y[1],x[2],y[2])

