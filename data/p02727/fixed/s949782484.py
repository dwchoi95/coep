x,y,a,b,c = (int(x) for x in input().split())

from bisect import insort

p_list = list(map(int,input().split()))
q_list = list(map(int,input().split()))
r_list = list(map(int,input().split()))


p_list.sort()
q_list.sort()
r_list.sort()

red = 0
green = 0
white = 0

sum_num = 0

for i in range(1,x+y+1):
  if red < x:
  	red_num = p_list[(red*-1)-1]
  else:
    red_num = 0
  if green < y:
  	green_num = q_list[(green*-1)-1]
  else:
    green_num = 0
  if white < c:
  	white_num = r_list[(white*-1)-1]
  else:
    white_num = 0
  
  max_p = max([red_num,green_num,white_num])
  sum_num += max_p
  if max_p == white_num:
    white += 1
  elif max_p == red_num:
    red += 1
  elif max_p == green_num:
    green += 1

print(sum_num)