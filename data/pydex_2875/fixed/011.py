# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
import string
n=int(input())
str=string.ascii_uppercase
result=""
for i in range(0, n):
 for j in range(0, i+1):
  result+="_"
  result+=str[j]
 result+="_"
 print(result, end= '\n')
 result=""