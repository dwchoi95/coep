

def decode_heap(target_list):
    for i, key in enumerate(target_list):
        node_index = i + 1
        parent_index = int(node_index / 2) - 1
        parent = ""
        if not parent_index < 0:
            parent = " parent key = " + str(target_list[parent_index]) + " "
            
        left_index = node_index * 2 - 1
        right_index = node_index * 2
        leaf = ""
        if left_index < len(target_list) and right_index < len(target_list):
            leaf = " left key ={}, right key = {}, ".format(target_list[left_index], target_list[right_index])

        print("node {}: key = {},{}{}".format(node_index, key, parent, leaf))

        
def main():
    n_nodes = int(input())
    target_list = [int(a) for a in input().split()]
    decode_heap(target_list)
    
if __name__ == "__main__":
    main()