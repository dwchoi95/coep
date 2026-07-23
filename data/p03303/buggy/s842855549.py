st = input()
skpe = int(input())
st_len = len(st)
count = st_len 
top_list = []

for i in range(count):
    top_list.append(st[3 * i:3 * i + 3])


for x in top_list:
    try:
        print(x[0], end="")
    except IndexError:
        pass
