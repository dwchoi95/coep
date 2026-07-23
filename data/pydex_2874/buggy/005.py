# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
def triangle(n): 
k = 2*n - 2
for i in range(0, n): 
for j in range(0, k): 
print(end=" ") 
k = k - 1
for j in range(0, i+1): 
print("* ", end="") 
print("\r") 
n = 3
triangle(n) 