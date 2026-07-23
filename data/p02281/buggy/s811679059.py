import sys

def walk(T, nid, order):
  if nid < 0: return
  lid, rid = T[nid]

  if order == "pre":
    sys.stdout.write(" " + str(nid))
    walk(T, lid, order)
    walk(T, rid, order)
  elif order == "in":
    walk(T, lid, order)
    sys.stdout.write(" " + str(nid))
    walk(T, rid, order)
  else:
    walk(T, lid, order)
    walk(T, rid, order)
    sys.stdout.write(" " + str(nid))

T = {}
for i in range(int(input())):
  nid, lid, rid = map(int, input().split())
  T[nid] = [lid, rid]

print("Preorder"),  walk(T, 0, "pre"),  print()
print("Inorder"),   walk(T, 0, "in"),   print()
print("Postorder"), walk(T, 0, "post"), print()