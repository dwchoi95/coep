def solve(n,a):
  even = 0
  
  for i in range(n):
    if a[i] % 2 == 0:
      even += 1
  
  return 3**n - 2**even
  
def main():
  N = int(input())
  a = list(map(int,input().split()))
  print(solve(N,a))
  
main()
