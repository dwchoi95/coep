import sys

def walk(T, nid, order):
  if nid < 0: return
  pid, lid, rid = T[nid]

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
  T[nid] = [-1, lid, rid]


for nid in T:
  pid, lid, rid = T[nid]
  if lid >= 0: T[lid][0] = nid
  if rid >= 0: T[rid][0] = nid


for nid in T:
  if T[nid][0] == -1: root_id = nid

print("Preorder"),  walk(T, root_id, "pre"),  print()
print("Inorder"),   walk(T, root_id, "in"),   print()
print("Postorder"), walk(T, root_id, "post"), print()