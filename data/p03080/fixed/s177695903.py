N = int(input())
red_num = 0
blue_num = 0
for i in input():
  if i == 'R':
    red_num += 1
  else:
    blue_num += 1
print('Yes' if red_num > blue_num else 'No')