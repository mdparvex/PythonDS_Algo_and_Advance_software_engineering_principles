# implement graph algorithm

class Graph:
    def __init__(self, routes):
        self.routes = routes

    def find_fath(self, start, end, path=[]):
        path = path + [start]

        if start==end:
            return [path]
        if start not in self.routes.keys():
            return None
        paths =[]

        for node in self.routes[start]:
            if node not in path:
                newpaths = self.find_fath(node,end,path)

                for newpath in newpaths:
                    paths.append(newpath)

        return paths


if __name__=="__main__":

    routes = {'A': ['B', 'C'],
             'B': ['C', 'D'],
             'C': ['D'],
             'D': ['C'],
             'E': ['F'],
             'F': ['C']
             }
    graph = Graph(routes)
    print(graph.find_fath('A','D'))