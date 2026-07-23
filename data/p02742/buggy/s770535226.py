H, W = map(int, input().split())
if W > 0:
	HW = H*W
	print(sum(divmod(HW, 2)))
else:
  print(0)