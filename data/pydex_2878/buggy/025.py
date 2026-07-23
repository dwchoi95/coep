# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
a = input()
data = []
d={}
for i in range((int(a))):
    data.append(input().split(','))
for x in data:
    keys = x[0]
    values = x[2]
    d[keys] = d.get(keys,0)+ int(values)
for k:v in d:
    print(k)
#         roll_num = x[0]
#         marks = x[2]
#         for r,m in zip(roll_num,marks):
#             print('Roll num {} has {} marks.'.format(r,m)
