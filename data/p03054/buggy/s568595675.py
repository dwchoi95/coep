


def main():
  L, R, U, D = 0, 1, 2, 3
  h, w, n = map(int, input().split())
  sr, sc = map(int, input().split())
  ls = input().strip()[::-1]
  lt = input().strip()[::-1]
  r = [0, w-1, 0, h-1]
  
  def f(d, x):
    if d=='L':
      r[L] = (min(max(0, r[L]-x), w-1) )
    if d=='R':
      r[R] = (min(max(0, r[R]+x), w-1) )
    if d=='U':
      r[U] = (min(max(0, r[U]-x), h-1) )
    if d=='D':
      r[D] = (min(max(0, r[D]+x), h-1) )
      
  def check():
    if r[L] >= r[R]:
      return False
    if r[U] >= r[D]:
      return False
    return True
  
  f(ls[0], 1)
  for s, t in zip(ls[1:], lt[1:]):
    f(s, 1)
    f(t, -1)
    if check():
      print('NO')
      return
  print('YES')
    
    
    

if __name__=='__main__':
  main()

