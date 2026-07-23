# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a, b = input().split(',')
x, ydef rev_number(n):
  s = 0
  while True:
    k = str(n)
    if k == k[::-1]:
      break
    else:
      m = int(k[::-1])
      n += m
      s += 1
  return n 