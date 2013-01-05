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
from graph import setupGraphs
import sys


class FSMCommander(Commander):
    numOfAttackers = 2
    numOfDefenders = 2
    numOfFlagGetters = 2
    edgeDistance = 10
    
    def reassignScouts(self, group, number):
        for _ in range(number):
            bot = self.scoutsGroup.getRandomBot()
            if bot:
                self.scoutsGroup.removeBot(bot)
                group.addBot(bot)
                
    def unassignScouts(self, group, number):
        for _ in range(len(group.bots) - number):
            bot = self.group.getRandomBot()
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
        setupGraphs(self) # inits self.graph
        self.getScoutingPositions()
        self.verbose = True
        self.bots = set()
        self.defenders = []
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
                self.defenders.append(bot)
            elif self.numOfDefenders <= i < self.numOfFlagGetters + self.numOfDefenders:
                self.flagGetters.append(bot)
            elif i %2 == 0:
                self.attackers.append(bot)
            else:
                self.scouts.append(bot)
                
        #TODO: priority decided based on distance
        teamPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), teamPosition) < 25 else 0
        self.defendingGroup = Squad(self.defenders, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=teamPriority, graph=self.graph, dirs=teamDirs))
        enemyPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), enemyPosition) < 25 else 0
        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner, priority=enemyPriority, graph=self.graph, dirs=[self.game.enemyTeam.flagScoreLocation - enemyPosition]))
        self.flagGroup = Squad(self.flagGetters, Goal(Goal.GETFLAG, None, None, graph=self.graph))
        self.scoutsGroup = Squad(self.scouts, Goal(Goal.PATROL, self.scoutPositions, None))
        self.squads = [self.defendingGroup, self.attackingGroup,self.flagGroup, self.scoutsGroup]
