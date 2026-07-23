# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
Input = int(input())
String_input = str(Input)
Reverse = String_input[ ::-1]
Sum = Input + int(Reverse)
Reverse_Integer= int(Reverse)
print("Reverse: " + str(Reverse_Integer))
print("Sum: " + str(Sum))