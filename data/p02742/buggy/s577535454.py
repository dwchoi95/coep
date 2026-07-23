h,w = (int(i) for i in input().split())

q_h,m_h = divmod(h,2)

if m_h == 0: 	
	print(w * q_h)
else:
	q_w,q_w = divmod(w,2)
	if q_w == 0:
		print(w * q_h + q_w)
	else:
		print(w * q_h + q_w + 1)