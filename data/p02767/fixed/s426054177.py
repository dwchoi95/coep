if __name__ == '__main__':
  num_resident = int(input())
  
  x_list = [int(a) for a in input().split()]
  min_x = min(x_list)
  max_x = max(x_list)
  
  fin_ps = 0
  for i in range(min_x, max_x + 1):
    sum_ps = 0
    for x_i in range(num_resident):
      sum_ps += pow((x_list[x_i] - i), 2)
    
    if(i == min_x):
      fin_ps = sum_ps 
      
    if(sum_ps < fin_ps):
      fin_ps = sum_ps
  
  print(fin_ps)
