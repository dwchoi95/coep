s = input()

slist = s.split(" ")

left = int(slist[0]) + int(slist[1])

right = int(slist[2]) + int(slist[3])

if left > right:
	print("Left")
	
elif left == right:
	print("Balanced")
	
else:
	print("Right")

