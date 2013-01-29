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

from pybrain.structure import FeedForwardNetwork
from pybrain.structure import LinearLayer, SigmoidLayer
from pybrain.structure import FullConnection
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer
#from pybrain.tools.xml.networkreader import NetworkReader


import pickle

import networkx as nx
# The maps for CTF are layed out along the X and Z axis in space, but can be
# effectively be considered 2D.
from bot import Bot, DefendingGroup, Squad, Goal
from states import  *

from util import distance

from visibility import *
from graph import setupGraphs
import sys
import os


class FSMCommander(Commander):
    numOfAttackers = 2
    numOfDefenders = 1
    numOfFlagGetters = 2
    edgeDistance = 10
    
    def reassign(self, toGroup, fromGroup, number):
        for _ in range(number):
            bot = fromGroup.getRandomBot()
            if bot:
                fromGroup.removeBot(bot)
                toGroup.addBot(bot)
                
    
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
        for node in nodes:
            self.updateWeights(node, 10)       
        self.graph = G
    
    def updateWeights(self, node, distance):
        weightAdded = 100
        if distance > 0:
            for i,j in [(1,0), (0,1), (-1,0), (0,-1)]:
                if self.squad.commander.inZone(node + Vector2(i, j)):
                    try:
                        if self.squad.commander.graph.has_edge(self.squad.commander.terrain[int(node.y)][int(node.x)], self.squad.commander.terrain[int(node.y+j)][int(node.x+i)]):
                            # we added this one before, just increase the weight by one
                            self.squad.commander.graph[self.squad.commander.terrain[int(node.y)][int(node.x)]][self.squad.commander.terrain[int(node.y+j)][int(node.x+i)]]['weight'] += weightAdded
                            self.updateWeights(Vector2(int(node.x+i), int(node.y+j)), distance - 1)
                    except:
                        pass
            
    def tick(self):
        #self.updateGraph()
        for squad in self.squads:
            squad.update()
            
    def isNearEdge(self, xory, position):
        if xory==0:
            return self.level.width - position.x < self.edgeDistance or position.x < self.edgeDistance
        else:
            return self.level.height - position.y < self.edgeDistance or position.y < self.edgeDistance
        
    
    def getStrategicPostion(self, position):
        minimum = sys.maxint
        index = Vector2(0,0)
        rangeOf = list(range(-5, 6)) + list(range(-5, 6))            
        rangeOf = [x for x in rangeOf if x != 0]            
        surroundingNodes = set(itertools.permutations(rangeOf, 2)) 
        for i,j in surroundingNodes:
            cells = []
            w = Wave((self.level.width, self.level.height), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
            positionTemp = self.level.findNearestFreePosition(Vector2(min(position.x + i, self.level.width-1),min(position.y + j, self.level.height-1)))
            w.compute(positionTemp)
            if len(cells) < minimum and canSee(positionTemp, position, self.level.width, self.level.height, lambda x, y: self.level.blockHeights[x][y] > 1):
                minimum = len(cells)
                position = positionTemp
        
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
        
    def getMostSecurePositions(self,secLoc):
        levelSize = (self.level.width, self.level.height)
        width, height = levelSize
        potPosits = [[0 for y in xrange(height)] for x in xrange(width)]
        neighbors = getVonNeumannNeighborhood((int(secLoc.x), int(secLoc.y)), self.level.blockHeights, int(self.level.firingDistance)-2)
        securePositions = []
        
        for n in neighbors:
            # use raycasting to test whether or not this position can see the flag
            # if it can't, automatically set it to 0
            x,y = n

            if self.level.blockHeights[x][y] >= 2:
                potPosits[x][y] = 50
            else:
                potPosits[x][y] = 255
                
            if potPosits[x][y] == 255:
                numWallCells = numAdjCoverBlocks(n, self.level.blockHeights)
                numWallCells += numAdjMapWalls(n, levelSize)
                #print numWallCells
                if numWallCells == 0:
                    potPosits[x][y] = 128
                if potPosits[x][y] == 255:
                    # make sure they have LOS with the flag
                    goodLOS = True
                    lookVec = Vector2(x+0.5,y+0.5) - (secLoc + Vector2(.5,.5))
                    lookVecNorm = lookVec.normalized()
                    vecInc = .1
                    while vecInc < lookVec.length():
                        testPos = secLoc + lookVecNorm * vecInc
                        #print str(testPos)
                        if self.level.blockHeights[int(testPos.x)][int(testPos.y)] >= 2:
                            goodLOS = False
                            break
                        vecInc += .1
                    if not goodLOS:
                        potPosits[x][y] = 128
                    else:
                        securePositions.append(n)
        #createPngFromMatrix(potPosits, levelSize)
        
        return sorted(securePositions, key = lambda p: numAdjMapWalls(p, levelSize)*4 + numAdjCoverBlocksWeighted(p, self), reverse = True)
                            
        
    def getPossiblePoints(self, position):
        rangeOf = list(range(-10, 11)) + list(range(-10, 11))            
        rangeOf = [x for x in rangeOf if x != 0]            
        surroundingNodes = set(itertools.permutations(rangeOf, 2))
        possibleVectors = set()
        blocks = numpy.array(self.level.blockHeights)
        for i,j in surroundingNodes:
            positionTemp = self.level.findNearestFreePosition(Vector2(min(position.x + i, self.level.width-1),min(position.y + j, self.level.height-1)))
            if blocks[min(position.x + i, self.level.width-1)][min(position.y + j, self.level.height-1)] == 0:
                possibleVectors.add(positionTemp)
        return list(possibleVectors)
            
        
        
    def getDefendingDirs(self, position):
        Vectors = [Vector2(0, 1), Vector2(1 , 0), Vector2(-1, 0), Vector2(0, -1)]
        ToFace = []
        for i in Vectors:
            if canSee(position, position + 7*i, self.level.width, self.level.height,lambda x, y: self.level.blockHeights[x][y] > 1):
                ToFace.append((i, 1))
        return ToFace
    

    def getAreaOfInterest(self, howFarFromFlags):
        xmin = max(0, min(self.game.team.flagSpawnLocation.x - howFarFromFlags, self.game.enemyTeam.flagSpawnLocation.x - howFarFromFlags))
        xmax = min(self.level.width, max(self.game.team.flagSpawnLocation.x + howFarFromFlags, self.game.enemyTeam.flagSpawnLocation.x +howFarFromFlags))
        ymin = max(0, min(self.game.team.flagSpawnLocation.y - howFarFromFlags, self.game.enemyTeam.flagSpawnLocation.y - howFarFromFlags))
        ymax = min(self.level.height, max(self.game.team.flagSpawnLocation.y + howFarFromFlags, self.game.enemyTeam.flagSpawnLocation.y + howFarFromFlags))
        return int(xmin), int(xmax), int(ymin), int(ymax)
    
    def findMinimumScorePosition(self):
        possiblePoints = self.getPossiblePoints(self.game.team.flag.position)
        inputField = numpy.array(self.level.blockHeights).reshape(1, self.level.width*self.level.height)
        inputField = tuple(tuple(x) for x in inputField)[0]     
        value = sys.maxint
        position = None
        for point in possiblePoints:
            inputFieldTemp = inputField + (point.x, point.y, self.game.team.flag.position.x, self.game.team.flag.position.y)
            if self.net.activate(inputFieldTemp) < value:
                position = point
        return position
    
    def clamp(self, x, minValue, maxValue):
        return max(minValue, min(x, maxValue))
    
    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width
    
    def filterInvalidDirs(self, position):
        Vector1 = Vector2(1, 0)
        Vector20 = Vector2(1, math.tan(math.radians(30)))
        Vector3 = Vector2(1, math.tan(math.radians(60)))
        Vector4 = Vector2(0, math.tan(math.radians(90)))
        Vector5 = Vector2(-1, -math.tan(math.radians(120)))
        Vector6 = Vector2(-1, -math.tan(math.radians(150)))
        Vector7 = Vector2(-1, math.tan(math.radians(180)))
        Vector8 = Vector2(-1, math.tan(math.radians(210)))
        Vector9 = Vector2(-1, math.tan(math.radians(240)))
        Vector10 = Vector2(0, -math.tan(math.radians(270)))
        Vector11 = Vector2(1, math.tan(math.radians(300)))
        Vector12 = Vector2(1, math.tan(math.radians(330)))
        Vectors = [Vector1, Vector20, Vector3, Vector4, Vector5, Vector6, Vector7, Vector8, Vector9, Vector10, Vector11, Vector12]
        Vectors = map(lambda x: x.normalized(), Vectors)
        Vectors = filter(lambda x: unblockedDistInDir(position, x, self) > self.level.firingDistance - 2, Vectors)
        Vectors = map(lambda x: (x, 1), Vectors)
        return list(set(Vectors))
    
    def initialize(self):      
        setupGraphs(self) # inits self.graph
        
        self.verbose = True
        self.bots = set()
        self.defenders = []
        self.attackers = []
        self.flagGetters = []
        self.scouts = []
        isTeamCorner = (0,0)        
        
        try:
            positions = self.getMostSecurePositions(self.game.team.flag.position)
            teamPositions = map(lambda x: Vector2(x[0], x[1]), positions)
            position = positions.pop()
            teamPosition = self.level.findNearestFreePosition(Vector2(position[0], position[1]))            
        except:
            teamPosition, _ = self.getStrategicPostion(self.game.team.flag.position)
        teamDirs = self.filterInvalidDirs(teamPosition)
                
        self.teamPosition = teamPosition
        enemyPosition, isEnemyCorner = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        
        try:
            positions = self.getMostSecurePositions(self.game.enemyTeam.flagScoreLocation)
            enemyPositions = map(lambda x: Vector2(x[0], x[1]), positions)
            position = positions.pop()
            enemyPosition = self.level.findNearestFreePosition(Vector2(position[0], position[1]))
        except:
            enemyPosition, _ = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        enemyDirs = self.filterInvalidDirs(enemyPosition)
        print enemyDirs
        try:
            positions = self.getMostSecurePositions(self.game.enemyTeam.flagSpawnLocation)
            position = positions.pop()
            safeLocation = self.level.findNearestFreePosition(Vector2(position[0], position[1]))
        except:
            safeLocation, _ = self.getStrategicPostion(self.game.enemyTeam.flagSpawnLocation)
        safeLocationDirs = self.filterInvalidDirs(safeLocation)
        
        teamFlagCloser = len(nx.shortest_path(self.graph, self.getNodeIndex(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea)), 
                                              self.getNodeIndex(self.game.team.flagSpawnLocation), 'weight')) < len(nx.shortest_path(self.graph,
                                              self.getNodeIndex(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea)), 
                                              self.getNodeIndex(self.game.enemyTeam.flagScoreLocation), 'weight'))
        
        for i, bot_info in enumerate(self.game.bots_available):
            bot = Bot(bot_info, self)
#            if i < self.numOfDefenders:                
#                self.defenders.append(bot)
#            elif self.numOfDefenders <= i < self.numOfFlagGetters + self.numOfDefenders:
#                self.flagGetters.append(bot)
#            elif i%2 == 0 or len(self.attackers) < 2:
#                if len(self.attackers) < 2 or teamFlagCloser:
#                    self.attackers.append(bot)
#                else:
            if i%2==0:
                self.attackers.append(bot)
            else:
                self.flagGetters.append(bot)
        
        #TODO: priority decided based on distance
#        teamPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), teamPosition) < 25 else 0
        self.defendingGroup = Squad(self.defenders, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=0, graph=self.graph, dirs=teamDirs[:min(len(self.defenders)*2, len(teamDirs))]), commander=self)
#        enemyPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), enemyPosition) < 25 else 0
        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner, priority=0, graph=self.graph, dirs=enemyDirs[:min(len(self.attackers)*2, len(enemyDirs))]), commander=self)
        
        
        self.flagGroup = Squad(self.flagGetters, Goal(Goal.GETFLAG, None, None, graph=self.graph, safeLoc=safeLocation, dirs=safeLocationDirs[:2]), commander=self)
        self.squads = [self.defendingGroup, self.attackingGroup, self.flagGroup]
    
    def getBlockHeightsNearFlag(self):
        flag = self.game.team.flagSpawnLocation
        xmin = flag.x - 5 if flag.x - 5 > 0 else 0
        xmax = flag.x + 5 if flag.x + 5 < self.level.width -1 else self.level.width - 1
        ymin = flag.y - 5 if flag.y - 5 > 0 else 0
        ymax = flag.y + 5 if flag.y + 5 < self.level.height -1 else self.level.height - 1
        blocks = numpy.array(self.level.blockHeights)
        return blocks[int(xmin):int(xmax), int(ymin):int(ymax)]
        
        
    def shutdown(self):
#        if self.flagAttackVectors:
#            while len(self.flagAttackVectors) < 6:
#                self.flagAttackVectors = self.flagAttackVectors + (0)
#            print self.flagAttackVectors[:6]
        
#        outputField = (self.game.match.scores[self.game.enemyTeam.name])
#        inputField = numpy.array(self.level.blockHeights).reshape(1, self.level.width*self.level.height)
#        inputField = tuple(tuple(x) for x in inputField)[0]
#        inputField = inputField + (self.teamPosition.x,  self.teamPosition.y, self.game.team.flagSpawnLocation.x, self.game.team.flagSpawnLocation.y)
#        #self.dataset.addSample(inputField, (outputField))
##        try:
##            trainer = BackpropTrainer(self.net, self.dataset)
##            trainer.trainEpochs(epochs=100)
##        except:
##            pass
##         
##         fileObject = open('network', 'w')
##         pickle.dump(self.net, fileObject)
#        with open('data.txt', 'a') as fileObject:
#			fileObject.write(str((inputField, (outputField)))+ '\n')
        Commander.shutdown(self)
