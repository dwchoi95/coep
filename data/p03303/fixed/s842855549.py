st = input()
skpe = int(input())
st_len = len(st)
count = (st_len 
top_list = []
s = ""

for i in range(count):
    top_list.append(st[skpe * i:skpe * i + skpe])


for x in top_list:
    try:
        s += x[0]
    except IndexError:
        pass
print(s)