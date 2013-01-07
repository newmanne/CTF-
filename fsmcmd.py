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
        
    def captured(self):
        """Did this team cature the enemy flag?"""
        return self.game.enemyTeam.flag.carrier != None
            
    def tick(self):
        if self.game.match.scores[self.game.team.name] > self.game.match.scores[self.game.enemyTeam.name] - 1:
            self.updateGraph()
            for squad in self.squads:
                squad.updateGraph(self.graph)
                squad.update()
        else:
            captured = self.captured()

            our_flag = self.game.team.flag.position
            their_flag = self.game.enemyTeam.flag.position
            their_base = self.level.botSpawnAreas[self.game.enemyTeam.name][0]
    
            # First process bots that are done with their orders...
            for bot in self.game.bots_available:
    
                # If this team has captured the flag, then tell this bot...
                if captured:
                    target = self.game.team.flagScoreLocation
                    # 1) Either run home, if this bot is the carrier or otherwise randomly.
                    if bot.flag is not None or (random.choice([True, False]) and (target - bot.position).length() > 8.0):
                        self.issue(commands.Charge, bot, target, description = 'scrambling home')
                    # 2) Run to the exact flag location, effectively escorting the carrier.
                    else:
                        self.issue(commands.Attack, bot, self.game.enemyTeam.flag.position, description = 'defending flag carrier',
                                   lookAt = random.choice([their_flag, our_flag, their_flag, their_base]))
    
                # In this case, the flag has not been captured yet so have this bot attack it!
                else:
                    path = [self.game.enemyTeam.flag.position]
                    if contains(self.level.botSpawnAreas[self.game.team.name], bot.position) and random.choice([True, False]):
                        path.insert(0, self.game.team.flagScoreLocation)
                    self.issue(commands.Attack, bot, path, description = 'attacking enemy flag',
                                    lookAt = random.choice([their_flag, our_flag, their_flag, their_base]))
    
            # Second process bots that are in a holding attack pattern.
            holding = len(self.game.bots_holding)
            for bot in self.game.bots_holding:
                if holding > 1:
                    self.issue(commands.Charge, bot, random.choice([b.position for b in bot.visibleEnemies]))
                else:
                    target = self.level.findRandomFreePositionInBox((bot.position-5.0, bot.position+5.0))
                    self.issue(commands.Attack, bot, target, lookAt = random.choice([b.position for b in bot.visibleEnemies]))
            
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
        
        position = position + index
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
        
    def getScoutingPositions(self):
        self.table = numpy.zeros((self.level.width, self.level.height))
        for i in range(self.level.width):
            for j in range(self.level.height):
                cells = []
                w = Wave((self.level.width, self.level.height), lambda x, y: self.level.blockHeights[x][y] > 1, lambda x, y: cells.append((x,y)))
                w.compute(Vector2(i, j))
                self.table[i][j] = len(cells)
        xmin, xmax, ymin, ymax = self.getAreaOfInterest(20)
        tempTable = self.table[xmin:xmax, ymin:ymax]
        reshaped = tempTable.reshape((xmax-xmin)*(ymax-ymin)) 
        mostVisible = reshaped.argsort()[-5:][::-1]
        self.scoutPositions = []
        for i in mostVisible:
            self.scoutPositions.append(self.level.findNearestFreePosition(Vector2(i/(ymax-ymin) + xmin, i%(xmax-xmin) + ymin)))
        self.scoutPositions.reverse()
        
    
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
            elif i %3 == 0 or len(self.attackers) < 2:
                self.attackers.append(bot)
            elif i %3 == 1:
                self.defenders.append(bot)
            else:
                self.flagGetters.append(bot)
                
        #TODO: priority decided based on distance
        teamPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), teamPosition) < 25 else 0
        self.defendingGroup = Squad(self.defenders, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=teamPriority, graph=self.graph, dirs=teamDirs), commander=self)
        enemyPriority = 1 if distance(self.level.findRandomFreePositionInBox(self.game.team.botSpawnArea), enemyPosition) < 25 else 0
        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner, priority=enemyPriority, graph=self.graph, dirs=[(self.game.enemyTeam.flagScoreLocation - enemyPosition, 1)]), commander=self)
        self.flagGroup = Squad(self.flagGetters, Goal(Goal.GETFLAG, None, None, graph=self.graph))
        self.scoutsGroup = Squad(self.scouts, Goal(Goal.PATROL, self.scoutPositions, None), self)
        self.squads = [self.defendingGroup, self.attackingGroup,self.flagGroup, self.scoutsGroup]
