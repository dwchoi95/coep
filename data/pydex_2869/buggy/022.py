# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
n = input()

	  num = str(n)
	  if num == num[::-1]:
	      sum = int(n)*2
	      print('Reverse:',num[::-1])
	      print('Sum:',sum)
	      break
	  else:
	      sum = int(n) + int(num[::-1])
	      print('Reverse:',num[::-1])
	      print('Sum:',sum)
	      break