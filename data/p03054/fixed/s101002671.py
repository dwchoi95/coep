


def main():
  L, R, U, D = 0, 1, 2, 3
  h, w, n = map(int, input().split())
  sr, sc = map(int, input().split())
  sr, sc = sr-1, sc-1
  ls = input().strip()[::-1]
  lt = input().strip()[::-1]
  r = [0, w-1, 0, h-1]
  
  def f(d):
    if d=='L':
      r[L] = (min(max(-1, r[L]+1), w))
    if d=='R':
      r[R] = (min(max(-1, r[R]-1), w))
    if d=='U':
      r[U] = (min(max(-1, r[U]+1), h))
    if d=='D':
      r[D] = (min(max(-1, r[D]-1), h))
      
  def g(d):
    if d=='L':
      r[R] = (min(max(0, r[R]+1), w-1))
    if d=='R':
      r[L] = (min(max(0, r[L]-1), w-1))
    if d=='U':
      r[D] = (min(max(0, r[D]+1), h-1))
    if d=='D':
      r[U] = (min(max(0, r[U]-1), h-1))
      
  def check():
    if r[L] > r[R] or r[L] < 0 or r[R] > w-1:
      return True
    if r[U] > r[D] or r[U] < 0 or r[D] > h-1:
      return True
    return False
  
  for s, t in zip(ls, lt):
    g(t)
    f(s)
    if check():
      print('NO')
      return
  if r[L] <= sc <= r[R] and r[U] <= sr <= r[D]:
    print('YES')
  else:
    print('NO')
    
if __name__=='__main__':
  main()

