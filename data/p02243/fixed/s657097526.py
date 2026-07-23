




import sys
import heapq as hp

WHITE, GRAY, BLACK = 0, 1, 2
D_MAX = int(5e10 + 1)


def generate_adj_matrix(v_info):
    for each in v_info:
        v_index, v_adj_length, *v_adj_list = map(int, each)
        
        for pair in zip(v_adj_list[::2], v_adj_list[1::2]):
            init_adj_matrix[v_index][pair[0]] = pair[1]

    return init_adj_matrix


def dijkstra_path():
    
    path_list[init_vertex_index] = 0
    path_heap = []
    
    hp.heappush(path_heap, (0, init_vertex_index))
    while len(path_heap) >= 1:
        current_vertex_index = hp.heappop(path_heap)[1]

        color[current_vertex_index] = BLACK

        current_vertex_index_info = adj_table[current_vertex_index]
        for adj_vertex_index in current_vertex_index_info.keys():
            current_adj_weight = current_vertex_index_info.get(adj_vertex_index)
            if color[adj_vertex_index] is not BLACK:
                
                alt_path = path_list[current_vertex_index] + current_adj_weight
                if alt_path < path_list[adj_vertex_index]:
                    
                    path_list[adj_vertex_index] = alt_path
                    
                    hp.heappush(path_heap, (alt_path, adj_vertex_index))
                    parent_list[adj_vertex_index] = current_vertex_index
                    color[adj_vertex_index] = GRAY

    return path_list


if __name__ == '__main__':
    _input = sys.stdin.readlines()
    vertices_num = int(_input[0])
    init_vertices_table = map(lambda x: x.split(), _input[1:])
    

    parent_list, path_list = [-1] * vertices_num, [D_MAX] * vertices_num
    color = [WHITE] * vertices_num
    init_adj_matrix = tuple(dict() for _ in range(vertices_num))
    init_vertex_index = 0

    adj_table = generate_adj_matrix(init_vertices_table)
    ans = dijkstra_path()
    for i, v in enumerate(ans):
        print(i, v)