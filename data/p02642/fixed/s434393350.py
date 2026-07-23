inf =  1100000
def main():
  N =  int(input())
  a = list(map(int, input().split()))
  a.sort()
  detect = [0] *inf
  for x in a:
    if detect[x] != 0:
      detect[x] = 2
      continue
    for i in range(x, inf, x):
      detect[i] += 1
  ans = 0
  for i in range(N):
    if detect[a[i]] == 1:
      ans += 1
  print(ans)
  
if __name__ == "__main__":
  main()