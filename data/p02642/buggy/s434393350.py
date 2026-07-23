inf =  1000005
def main():
  N =  int(input())
  a = list(map(int, input().split()))
  a.sort()
  detect = [0] *inf
  for i in range(N):
    detect[a[i]] += 1
    if detect[a[i]] >= 2:
      continue
    j = 2
    while (a[i]*j < inf):
      if detect[a[i]*j] >= 2:
        break
      else:
        detect[a[i]*j] += 2
        j+=1
  ans = 0
  for i in range(N):
    if detect[a[i]] == 1:
      ans += 1
  print(ans)
  
if __name__ == "__main__":
  main()