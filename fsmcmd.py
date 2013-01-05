# Your AI for CTF must inherit from the base Commander class.  See how this is
# implemented by looking at the commander.py in the ./api/ folder.
import api
from api.gameinfo import *
from api import *

import math
import itertools
import random
import numpy
import scipy
import itertools

import networkx as nx
# The maps for CTF are layed out along the X and Z axis in space, but can be
# effectively be considered 2D.
from bot import Bot, DefendingGroup, Squad, Goal
from states import  *

from util import distance

from visibility import *
import sys


class FSMCommander(Commander):
    
    edgeDistance = 10
    
    def reassignScouts(self, group, number):
        for _ in range(number):
            bot = self.scoutsGroup.getRandomBot()
            if bot:
                self.scoutsGroup.removeBot(bot)
                group.addBot(bot)
                
    def unassignScouts(self, group, number):
        for _ in range(len(group.bots) - number):
            bot = group.getRandomBot()
            if bot:
                self.scoutsGroup.addBot(bot)
                group.removeBot(bot)
    
    def getVisibleEnemies(self):
        enemies = set()
        for bot in self.game.bots_alive:
            enemies.union(set(bot.visibleEnemies))
        return enemies
    
    def inZone(self, position):
        if position.x < 0 or position.x > self.level.width -1:
            return False
        if position.y < 0 or position.y > self.level.height -1:
            return False
        return True        
    
    def updateGraph(self):
        self.graph = self.originalGraph
        enemies = self.getVisibleEnemies()
        nodes = map(lambda x: x.position, enemies)
        G = self.graph
        weightAdded = 5
        for node in nodes:
            rangeOf = list(range(-5, 6)) + list(range(-5, 6))            
            rangeOf = [x for x in rangeOf if x != 0]            
            surroundingNodes = set(itertools.permutations(rangeOf, 2))                  
            for i,j in surroundingNodes:
                if self.inZone(node + Vector2(i, j)):
                    if G.has_edge(self.terrain[node.x][node.y], self.terrain[node.x+i][node.y+j]):
                        # we added this one before, just increase the weight by one
                        G[self.terrain[node.x][node.y]][self.terrain[node.x+i][node.y+j]]['weight'] += weightAdded/math.hypot(i, j)        
        self.graph = G
            
    def tick(self):
        if self.greed:
            self.squads[0].update()
            return
        self.updateGraph()
        for squad in self.squads:
            if not [bot for bot in squad.bots if bot.health >0] and squad == self.defendingGroup:
                self.reassignScouts(self.defendingGroup, self.numOfDefenders)
            if len(squad.bots) > self.numOfDefenders and squad == self.defendingGroup:
                self.unassignScouts(self.defendingGroup, self.numOfDefenders)
            squad.updateGraph(self.graph)
            squad.update()
            
    def isNearEdge(self, xory, position):
        if xory==0:
            return self.level.width - position.x < self.edgeDistance or position.x < self.edgeDistance
        else:
            return self.level.height - position.y < self.edgeDistance or position.y < self.edgeDistance
    


    def getStrategicPostion(self, position):
        minimum = sys.maxint
        for i in range(5):
            for j in range(5):
                cells = []
                w = Wave((self.level.width, self.level.height), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
                w.compute(Vector2(min(position.x + i, self.level.width-1),min(position.y + j, self.level.height-1)))
                if len(cells) < minimum and canSee(position + Vector2(i, j), position, self.level.width, self.level.height, lambda x, y: self.level.blockHeights[x][y] > 1):
                    minimum = len(cells)
                    index = Vector2(i, j)
                w.compute(Vector2(max(position.x - i, 0),min(position.y + j, self.level.height-1)))
                if len(cells) < minimum and canSee(position + Vector2(i, -j), position, self.level.width, self.level.height, lambda x, y: self.level.blockHeights[x][y] > 1):
                    minimum = len(cells)
                    index = Vector2(i, -j)
                w.compute(Vector2(min(position.x + i, self.level.width-1),max(position.y - j, 0)))
                if len(cells) < minimum and canSee(position + Vector2(-i, j), position, self.level.width, self.level.height, lambda x, y: self.level.blockHeights[x][y] > 1):
                    minimum = len(cells)
                    index = Vector2(-i, j)
                w.compute(Vector2(max(position.x - i, 0),max(position.y - j, 0)))
                if len(cells) < minimum and canSee(position + Vector2(-i, -j), position, self.level.width, self.level.height, lambda x, y: self.level.blockHeights[x][y] > 1):
                    minimum = len(cells)
                    index = Vector2(-i, -j)
        
        position= position + index
        if self.isNearEdge(0, position) and self.isNearEdge(1, position):
            isCorner = (1 if position.x < self.edgeDistance else -1, 1 if position.y < self.edgeDistance else -1)
            return Vector2(0 if position.x < self.edgeDistance else self.level.width , 0 if position.y < self.edgeDistance else self.level.height), isCorner
        elif self.isNearEdge(0, position):
            isCorner = (1 if position.x < self.edgeDistance else -1, 0)
            return Vector2(0 if position.x < self.edgeDistance else self.level.width , position.y), isCorner
        elif self.isNearEdge(1, position):
            isCorner = (0, 1 if position.y < self.edgeDistance else -1)
            return Vector2(position.x, 0 if position.y < self.edgeDistance else self.level.height), isCorner
        else:
            return position, (0,0)
        
        
    def getDefendingDirs(self, position):
        VectorOne = Vector2(0, 1)
        VectorTwo = Vector2(1 , 0)
        VectorThree = Vector2(-1, 0) 
        VectorFour = Vector2(0, -1)
        Vectors = [VectorOne, VectorTwo, VectorThree, VectorFour]
        ToFace = []
        for i in Vectors:
            if canSee(position, position + 7*i, self.level.width, self.level.height,lambda x, y: self.level.blockHeights[x][y] > 1):
                ToFace.append((i, 1))
        return ToFace
        
    def getScoutingPositions(self):
        self.table = numpy.zeros((self.level.width, self.level.height))
        for i in range(self.level.width):
            for j in range(self.level.height):
                cells = []
                w = Wave((self.level.width, self.level.height), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
                w.compute(Vector2(i, j))
                self.table[i][j] = len(cells)
        tempTable = self.table[10:self.level.width-10][:]
        reshaped = tempTable.reshape((self.level.width-20)*self.level.height) 
        mostVisible = reshaped.argsort()[-10:][::-1]
        self.scoutPositions = []
        for i in mostVisible:
            self.scoutPositions.append(self.level.findNearestFreePosition(Vector2(i/(self.level.width-20), i%self.level.height)))
    
    def initialize(self):
        if self.game.bots_alive > 10:
            self.squads = [Squad(self.game.bots_alive, Goal(Goal.GREED), self)]
            self.greed = True
            return
        self.numOfDefenders = 2
        self.numOfFlagGetters = 2
        self.setupGraps()
        self.getScoutingPositions()
        self.verbose = True
        self.bots = set()
        self.bots = []
        self.attackers = []
        self.flagGetters = []
        self.scouts = []
        teamPosition, isTeamCorner = self.getStrategicPostion(self.game.team.flag.position)
        teamPosition = self.level.findNearestFreePosition(teamPosition)
        teamDirs = self.getDefendingDirs(teamPosition)
        enemyPosition, isEnemyCorner = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        enemyPosition = self.level.findNearestFreePosition(enemyPosition)
        enemyDirs = self.getDefendingDirs(enemyPosition)
        for i, bot_info in enumerate(self.game.bots_available):
            bot = Bot(bot_info, self)
            if i < self.numOfDefenders:                
                self.bots.append(bot)
            elif self.numOfDefenders < i < self.numOfFlagGetters + self.numOfDefenders:
                self.flagGetters.append(bot)
            elif i % 2 == 0:
                self.attackers.append(bot)
            else:
                self.scouts.append(bot)
                
        #TODO: priority decided based on distance
        teamPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), teamPosition) < 25 else 0
        self.defendingGroup = Squad(self.bots, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=teamPriority, graph=self.graph, dirs=teamDirs))
        enemyPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), enemyPosition) < 25 else 0
        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner, priority=enemyPriority, graph=self.graph, dirs=[self.game.enemyTeam.flagScoreLocation - enemyPosition]))
        self.flagGroup = Squad(self.flagGetters, Goal(Goal.GETFLAG, None, None, graph=self.graph))
        self.scoutsGroup = Squad(self.scouts, Goal(Goal.PATROL, self.scoutPositions, None))
        self.squads = [self.defendingGroup, self.attackingGroup,self.flagGroup, self.scoutsGroup]
        
        
    def setupGraps(self):
        self.makeGraph()
        
        self.graph.add_node("enemy_base")
        self.positions["enemy_base"] = None
        start, finish = self.level.botSpawnAreas[self.game.enemyTeam.name]
        for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
            self.graph.add_edge("enemy_base", self.terrain[j][i], weight = 1.0)

        self.graph.add_node("base")
        self.positions["base"] = None
        start, finish = self.level.botSpawnAreas[self.game.team.name]
        for i, j in itertools.product(range(int(start.x), int(finish.x)), range(int(start.y), int(finish.y))):
            self.graph.add_edge("base", self.terrain[j][i], weight = 1.0)

        self.node_EnemyFlagIndex = self.getNodeIndex(self.game.team.flag.position)
        self.node_EnemyScoreIndex = self.getNodeIndex(self.game.enemyTeam.flagScoreLocation)

        # self.node_Bases = self.graph.add_vertex()
        # e = self.graph.add_edge(self.node_Bases, self.node_MyBase)
        # e = self.graph.add_edge(self.node_Bases, self.node_EnemyBase)

        vb2f = nx.shortest_path(self.graph, source="enemy_base", target=self.node_EnemyFlagIndex)
        vf2s = nx.shortest_path(self.graph, source=self.node_EnemyFlagIndex, target=self.node_EnemyScoreIndex)
        #vb2s = nx.shortest_path(self.graph, source="enemy_base", target=self.node_EnemyScoreIndex)

        self.node_EnemyBaseToFlagIndex = "enemy_base_to_flag"
        self.graph.add_node(self.node_EnemyBaseToFlagIndex)
        self.positions["enemy_base_to_flag"] = None
        for vertex in vb2f:
            self.graph.add_edge(self.node_EnemyBaseToFlagIndex, vertex, weight = 1.0)
        
        self.node_EnemyFlagToScoreIndex = "enemy_flag_to_score" 
        self.graph.add_node(self.node_EnemyFlagToScoreIndex)
        self.positions["enemy_flag_to_score"] = None
        for vertex in vf2s:
            self.graph.add_edge(self.node_EnemyFlagToScoreIndex, vertex, weight = 1.0)
        
        self.node_EnemyBaseToScoreIndex = "enemy_base_to_score"
        self.graph.add_node(self.node_EnemyBaseToScoreIndex)
        self.positions["enemy_base_to_score"] = None
       # for vertex in vb2s:
       #     self.graph.add_edge(self.node_EnemyBaseToScoreIndex, vertex, weight = 1.0)

        ## node = self.makeNode(self.game.enemyTeam.flag.position)
        self.distances = nx.single_source_shortest_path_length(self.graph, self.node_EnemyFlagToScoreIndex)

        self.graph.remove_node("base")
        self.graph.remove_node("enemy_base")
        self.graph.remove_node(self.node_EnemyBaseToFlagIndex)
        self.graph.remove_node(self.node_EnemyFlagToScoreIndex)
        self.graph.remove_node(self.node_EnemyBaseToScoreIndex)

        self.updateEdgeWeights()

        self.paths = {b: None for b in self.game.team.members}
        self.originalGraph = self.graph
    
    def getDistance(self, x, y):
        n = self.terrain[y][x]
        if n:
            return self.distances[n]
        else:
            return 0.0
    def makeGraph(self):
        blocks = self.level.blockHeights
        width, height = len(blocks), len(blocks[0])

        g = nx.Graph(directed=False, map_height = height, map_width = width)
        #self.positions = g.new_vertex_property('vector<float>')
        #self.weights = g.new_edge_property('float')
    
        #g.vertex_properties['pos'] = self.positions
        #g.edge_properties['weight'] = self.weights
    
        self.terrain = []
        self.positions = {}
        for j in range(0, height):
            row = []
            for i in range(0,width):
                if blocks[i][j] == 0:
                    g.add_node(i+j*width, position = (float(i)+0.5, float(j)+0.5) )
                    self.positions[i+j*width] = Vector2(float(i) + 0.5, float(j) + 0.5)
                    row.append(i+j*width)
                else:
                    row.append(None)
            self.terrain.append(row)
        
        for i, j in itertools.product(range(0, width), range(0, height)):
            p = self.terrain[j][i]
            if not p: continue
    
            if i < width-1:
                q = self.terrain[j][i+1]
                if q:
                    e = g.add_edge(p, q, weight = 1.0)
    
            if j < height-1:
                r = self.terrain[j+1][i]
                if r:
                    e = g.add_edge(p, r, weight = 1.0)
    
        self.graph = g

    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width


    def updateEdgeWeights(self):
        blocks = self.level.blockHeights
        width, height = len(blocks), len(blocks[0])

        # update the weights in the graph based on the distance to the shortest path between the enemy flag and enemy score location

        for j in range(0, height):
            for i in range(0, width -1):
                a = self.terrain[j][i]
                b = self.terrain[j][i+1]
                if a and b:
                    w = max(255 - 4*(self.distances[a] + self.distances[b]), 0)
                    self.graph[a][b]['weight'] = w

        for j in range(0, height-1):
            for i in range(0, width):
                a = self.terrain[j][i]
                b = self.terrain[j+1][i]
                if a and b:
                    w = max(255 - 4*(self.distances[a] + self.distances[b]), 0)
                    self.graph[a][b]['weight'] = w