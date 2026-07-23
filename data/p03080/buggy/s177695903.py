N = int(input())
red_num = 0
for i in input():
  if i == 'R':
    red_num += 1
print('Yes' if red_num > N else 'No')