import itertools
import networkx as nx
from api import Vector2

def setupGraphs(commander):
    makeGraph(commander)
    weightAdded = 10.0
    commander.graph.add_node("enemy_base")
    commander.positions["enemy_base"] = None
    start, finish = commander.level.botSpawnAreas[commander.game.enemyTeam.name]
    for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
        commander.graph.add_edge("enemy_base", commander.terrain[j][i], weight=weightAdded)

    commander.graph.add_node("base")
    commander.positions["base"] = None
    start, finish = commander.level.botSpawnAreas[commander.game.team.name]
    for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
        commander.graph.add_edge("base", commander.terrain[j][i], weight=weightAdded)

    node_EnemyFlagIndex = getNodeIndex(commander, commander.game.team.flag.position)
    node_EnemyScoreIndex = getNodeIndex(commander, commander.game.enemyTeam.flagScoreLocation)

    # self.node_Bases = commander.graph.add_vertex()
    # e = commander.graph.add_edge(self.node_Bases, self.node_MyBase)
    # e = commander.graph.add_edge(self.node_Bases, self.node_EnemyBase)

    vb2f = nx.dijkstra_path(commander.graph, source="enemy_base", target=node_EnemyFlagIndex)
    vf2s = nx.dijkstra_path(commander.graph, source=node_EnemyFlagIndex, target=node_EnemyScoreIndex)
    # vb2s = nx.shortest_path(commander.graph, source="enemy_base", target=self.node_EnemyScoreIndex)

    node_EnemyBaseToFlagIndex = "enemy_base_to_flag"
    commander.graph.add_node(node_EnemyBaseToFlagIndex)
    commander.positions["enemy_base_to_flag"] = None
    for vertex in vb2f:
        commander.graph.add_edge(node_EnemyBaseToFlagIndex, vertex, weight=weightAdded)
    
    node_EnemyFlagToScoreIndex = "enemy_flag_to_score" 
    commander.graph.add_node(node_EnemyFlagToScoreIndex)
    commander.positions["enemy_flag_to_score"] = None
    for vertex in vf2s:
        commander.graph.add_edge(node_EnemyFlagToScoreIndex, vertex, weight=weightAdded)
    
    node_EnemyBaseToScoreIndex = "enemy_base_to_score"
    commander.graph.add_node(node_EnemyBaseToScoreIndex)
    commander.positions["enemy_base_to_score"] = None
   # for vertex in vb2s:
   #     commander.graph.add_edge(self.node_EnemyBaseToScoreIndex, vertex, weight = weightAdded)

    # # node = self.makeNode(commander.game.enemyTeam.flag.position)
    distances = nx.single_source_shortest_path_length(commander.graph, node_EnemyFlagToScoreIndex)

    commander.graph.remove_node("base")
    commander.graph.remove_node("enemy_base")
    commander.graph.remove_node(node_EnemyBaseToFlagIndex)
    commander.graph.remove_node(node_EnemyFlagToScoreIndex)
    commander.graph.remove_node(node_EnemyBaseToScoreIndex)

    updateEdgeWeights(commander, distances)

    commander.originalGraph = commander.graph

def makeGraph(commander):
    blocks = commander.level.blockHeights
    width, height = len(blocks), len(blocks[0])

    g = nx.Graph(directed=False, map_height=height, map_width=width)
    # commander.positions = g.new_vertex_property('vector<float>')
    # self.weights = g.new_edge_property('float')

    # g.vertex_properties['pos'] = commander.positions
    # g.edge_properties['weight'] = self.weights

    commander.terrain = []
    commander.positions = {}
    for j in range(0, height):
        row = []
        for i in range(0, width):
            if blocks[i][j] == 0:
                g.add_node(i + j * width, position=(float(i) + 0.5, float(j) + 0.5))
                commander.positions[i + j * width] = Vector2(float(i) + 0.5, float(j) + 0.5)
                row.append(i + j * width)
            else:
                row.append(None)
        commander.terrain.append(row)
    
    for i, j in itertools.product(range(0, width), range(0, height)):
        p = commander.terrain[j][i]
        if not p: continue

        if i < width - 1:
            q = commander.terrain[j][i + 1]
            if q:
                e = g.add_edge(p, q, weight=1.0)

        if j < height - 1:
            r = commander.terrain[j + 1][i]
            if r:
                e = g.add_edge(p, r, weight=1.0)
    commander.graph = g

def getNodeIndex(commander, position):
    i = int(position.x)
    j = int(position.y)
    width = commander.graph.graph["map_width"]
    return i + j * width

def updateEdgeWeights(commander, distances):
    blocks = commander.level.blockHeights
    width, height = len(blocks), len(blocks[0])

    # update the weights in the graph based on the distance to the shortest path between the enemy flag and enemy score location

    for j in range(0, height):
        for i in range(0, width - 1):
            a = commander.terrain[j][i]
            b = commander.terrain[j][i + 1]
            if a and b:
                w = max(255 - 4 * (distances[a] + distances[b]), 0)
                commander.graph[a][b]['weight'] = w

    for j in range(0, height - 1):
        for i in range(0, width):
            a = commander.terrain[j][i]
            b = commander.terrain[j + 1][i]
            if a and b:
                w = max(255 - 4 * (distances[a] + distances[b]), 0)
                commander.graph[a][b]['weight'] = w
