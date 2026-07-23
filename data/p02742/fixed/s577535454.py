h,w = (int(i) for i in input().split())

q_h,mod_h = divmod(h,2)

if h == 1 or w == 1:
	print(1)
elif mod_h == 0: 	
	print(w * q_h)
else:
	q_w,mod_w = divmod(w,2)
	if mod_w == 0:
		print(w * q_h + q_w)
	else:
		print(w * q_h + q_w + 1)