H, W = map(int, input().split())
if H!=1 and W!=1:
	HW = H*W
	print(sum(divmod(HW, 2)))
else:
  print(1)