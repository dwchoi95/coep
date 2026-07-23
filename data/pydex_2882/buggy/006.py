# compile-errors:success: Compilation Successful #
# compile-result:1 #
# save-event:compile #
ef a(m,n,T):
    global cnt
    cnt += 1
    if cnt>T:
        return False
    elif m == 0:
        return n+1
    elif n == 0:
        return a(m-1,1,T)
    return a(m-1,a(m,n-1,T),T)

x,y,t = input().split(',')
m,n,T = int(x),int(y),int(t)
cnt = 0

res = a(m,n,T)
if not res:
    print('Aborted')
else:
    print('Result = {} in {} calls'.format(res,cnt))