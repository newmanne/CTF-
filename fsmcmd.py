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


class FSMCommander(Commander):
    numOfAttackers = 2
    numOfDefenders = 2
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
        inputField = self.getBlockHeightsNearFlag().reshape(1,100)
        inputField = tuple(tuple(x) for x in inputField)[0]       
        value = sys.maxint
        position = None
        for point in possiblePoints:
            inputFieldTemp = inputField + (point.x, point.y, self.game.team.flag.position.x, self.game.team.flag.position.y)
            if self.net.activate(inputFieldTemp) < value:
                position = point
        return position
    
    def initialize(self):
        try:
            fileObject = open('network','r')
            self.net = pickle.load(fileObject)
            fileObject = open('data','r')
            self.dataset = pickle.load(fileObject)
            print "Found previous network"
            teamPosition = random.choice(self.getPossiblePoints(self.game.team.flag.position))
            
        except:
            self.net = FeedForwardNetwork()
            inputLayer = LinearLayer(self.level.width*self.level.height + 4)
            hiddenLayer = SigmoidLayer(66)
            outLayer = LinearLayer(1)
            self.net.addInputModule(inputLayer)
            self.net.addModule(hiddenLayer)
            self.net.addOutputModule(outLayer)
            in_to_hidden = FullConnection(inputLayer, hiddenLayer)
            hidden_to_out = FullConnection(hiddenLayer, outLayer)
            self.net.addConnection(in_to_hidden)
            self.net.addConnection(hidden_to_out)
            self.net.sortModules()
            self.dataset = SupervisedDataSet(self.level.width*self.level.height + 4, 1)
            print "Didn't find previous network"
            teamPosition = random.choice(self.getPossiblePoints(self.game.team.flag.position))
            
#        teamPosition = self.findMinimumScorePosition()
        setupGraphs(self) # inits self.graph
        self.verbose = True
        self.bots = set()
        self.defenders = []
        self.attackers = []
        self.flagGetters = []
        self.scouts = []
        isTeamCorner = (0,0)        
        self.teamPosition = teamPosition
        
        teamDirs = self.getDefendingDirs(teamPosition)
        enemyPosition, isEnemyCorner = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        enemyPosition = self.level.findNearestFreePosition(enemyPosition)
        enemyDirs = self.getDefendingDirs(enemyPosition)
        for i, bot_info in enumerate(self.game.bots_available):
            bot = Bot(bot_info, self)
            if i < self.numOfDefenders:                
                self.defenders.append(bot)
#            elif self.numOfDefenders <= i < self.numOfFlagGetters + self.numOfDefenders:
#                self.flagGetters.append(bot)
#            elif i %3 == 0 or len(self.attackers) < 2:
#                self.attackers.append(bot)
#            elif i %3 == 1:
#                self.defenders.append(bot)
#            else:
#                self.flagGetters.append(bot)
                
        #TODO: priority decided based on distance
        teamPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), teamPosition) < 25 else 0
        self.defendingGroup = Squad(self.defenders, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=teamPriority, graph=self.graph, dirs=teamDirs), commander=self)
#        enemyPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), enemyPosition) < 25 else 0
#        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner, priority=enemyPriority, graph=self.graph, dirs=[(self.game.enemyTeam.flagScoreLocation - enemyPosition, 1)]), commander=self)
#        self.flagGroup = Squad(self.flagGetters, Goal(Goal.GETFLAG, None, None, graph=self.graph))
        self.squads = [self.defendingGroup]
    
    def getBlockHeightsNearFlag(self):
        flag = self.game.team.flagSpawnLocation
        xmin = flag.x - 5 if flag.x - 5 > 0 else 0
        xmax = flag.x + 5 if flag.x + 5 < self.level.width -1 else self.level.width - 1
        ymin = flag.y - 5 if flag.y - 5 > 0 else 0
        ymax = flag.y + 5 if flag.y + 5 < self.level.height -1 else self.level.height - 1
        blocks = numpy.array(self.level.blockHeights)
        return blocks[int(xmin):int(xmax), int(ymin):int(ymax)]
        
        
    def shutdown(self):
        outputField = (self.game.match.scores[self.game.enemyTeam.name])
        inputField = numpy.array(self.level.blockHeights).reshape(1, self.level.width*self.level.height)
        inputField = tuple(tuple(x) for x in inputField)[0]
        inputField = inputField + (self.teamPosition.x,  self.teamPosition.y, self.game.team.flagSpawnLocation.x, self.game.team.flagSpawnLocation.y)
        self.dataset.addSample(inputField, (outputField))
#        try:
#            trainer = BackpropTrainer(self.net, self.dataset)
#            trainer.trainEpochs(epochs=100)
#        except:
#            pass
        
        fileObject = open('network', 'w')
        pickle.dump(self.net, fileObject)
        
        fileObject = open('data', 'w')
        pickle.dump(self.dataset, fileObject)
        Commander.shutdown(self)
