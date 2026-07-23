N, M = map(int, input().split())  

ans = 0





shop_list = []
for _ in range(N):
    hoge = {}
    A, B = map(int, input().split())
    hoge['price'] = A
    hoge['amount'] = B
    shop_list.append(hoge)
    hoge = {}

shop_list.sort(key=lambda x: x['price'])

quontity = 0
money = 0
for i in range(len(shop_list)):
    money += shop_list[i]['price']*shop_list[i]['amount']
    
    quontity += shop_list[i]['amount']
    
    if quontity >= M:
        money -= shop_list[i]['price']*(quontity-M)

print(money)
