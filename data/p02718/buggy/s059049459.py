import math

def solve(n,m,lst):
  min_vote = math.ceil(sum(lst)/4/m) - 1
  print(min_vote)
  print(sum(lst))
  return lst[m-1] > min_vote

if __name__ == "__main__":
  _n, _m = map(int, input().split())
  a_list = [int(i) for i in input().split()]
  a_list = sorted(a_list,reverse=True)
  if solve(_n,_m,a_list):
    print('Yes')
  else:
    print('No')
