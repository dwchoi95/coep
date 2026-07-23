def physical_strength(x,p):
  return pow((x - p), 2)



if __name__ == '__main__':
  num_resident = input()
  x_list = [int(a) for a in input().split()]
  min_x = min(x_list)
  max_x = max(x_list)
  
  fin_ps = pow(max_x, 2)
  for i in range(min_x, max_x + 1):
    sum_ps = 0
    for x in x_list:
      sum_ps += physical_strength(x, i)
    if(sum_ps < fin_ps):
      fin_ps = sum_ps
  
  print(fin_ps)
