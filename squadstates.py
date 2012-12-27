from api import Vector2
from util import *
from states import *

import random

import networkx as nx
from api.gameinfo import BotInfo

       
class Attack():
    def __init__(self, squad, position, isCorner, priority, graph):
        self.squad = squad
        self.bots = squad.bots
        self.position = position
        self.isCorner = isCorner
        self.priority = priority
        self.graph = graph
        self.paths = {}
        
    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width
        
    def sneak(self, bot):   
        srcIndex = self.getNodeIndex(bot.position)
        dstIndex = self.getNodeIndex(self.position)
        pathNodes = nx.shortest_path(self.graph, srcIndex, dstIndex, 'weight')
        pathLength = len(pathNodes)
        if pathLength > 0:
            path = [self.bots[0].commander.positions[p] for p in pathNodes if self.bots[0].commander.positions[p]]
            if len(path) > 0:
                orderPath = path[::10]
                orderPath.append(path[-1]) # take every 10th point including last point
                self.paths[bot] = orderPath    # store the path for visualization
    
    def execute(self):
        
        arrived = map(lambda x: inArea(x.position, self.position), self.bots)
        arrived = reduce(lambda x,y:x and y, arrived)
        if arrived:
            self.squad.changeState(self.squad.prevState.pop())
            return
        idle = map(lambda x: x.state == BotInfo.STATE_IDLE, self.bots)
        idle = reduce(lambda x,y:x and y, idle)
        if(self.priority == 0 and idle):
            for bot in self.bots:
                self.sneak(bot)
                bot.changeState(ChargePosition(bot, self.paths[bot]))
        else:
            for bot in self.bots:
                bot.update()
        
    def enter(self):        
        for bot in self.bots:
            if(self.priority == 0):
                self.sneak(bot)
                bot.changeState(ChargePosition(bot, self.paths[bot]))
            else:
                bot.changeState(ChargePosition(bot, bot.commander.level.findNearestFreePosition(self.position)))
    
    def exit(self):
        pass

class Defend():
    #Right Side
    VectorOne = (Vector2(0.268, 1), 1)
    VectorTwo = (Vector2(1 , 1), 1)
    VectorThree = (Vector2(1, 0.268), 1)
    
    CornerBottomLeft = [VectorOne, VectorTwo, VectorThree]
    
    VectorFour = (Vector2(1, -0.268), 1)
    VectorFive = (Vector2(1, -1), 1)
    VectorSix = (Vector2(0.268, -1), 1)
    
    CornerTopLeft = [VectorFour, VectorFive, VectorSix]
    
    VectorSeven = (Vector2(-0.268, 1), 1)
    VectorEight = (Vector2(-1 , 1), 1)
    VectorNine = (Vector2(-1, 0.268), 1)
    
    CornerBottomRight = [VectorSeven, VectorEight, VectorNine]
    
    VectorTen = (Vector2(-1, -0.268), 1)
    VectorEleven = (Vector2(-1, -1), 1)
    VectorTwelve = (Vector2(-0.268, -1), 1)
    
    CornerTopRight = [VectorTen, VectorEleven, VectorTwelve]
    
    Vectors = [VectorOne, VectorTwo, VectorThree, VectorFour, VectorFive, VectorSix, VectorSeven, VectorEight, VectorNine,VectorTen, VectorEleven, VectorTwelve] 
    
    up = (Vector2(0, 1), 1)
    down = (Vector2(0, -1), 1)
    left = (Vector2(-1, 0), 1)
    right = (Vector2(1, 0), 1)
    
    
    def assignVector(self):
        if(self.isCorner == (0,0)):
            return
        elif(self.isCorner == (1,0)):
            self.Vectors = self.CornerBottomLeft + self.CornerTopLeft
        elif(self.isCorner == (-1,0)):
            self.Vectors = self.CornerBottomRight + self.CornerTopRight
        elif(self.isCorner == (0,1)):
            self.Vectors = [(Vector2(1,1), 1),  (Vector2(-1,1), 1)]
        elif(self.isCorner == (0,-1)):
            self.Vectors = [(Vector2(1,-1), 1),  (Vector2(-1,-1), 1)]
        elif(self.isCorner == (1,1)):
            self.Vectors = self.CornerBottomLeft
        elif(self.isCorner == (1,-1)):
            self.Vectors = self.CornerTopLeft
        elif(self.isCorner == (-1,1)):
            self.Vectors = self.CornerBottomRight
        elif(self.isCorner == (-1,-1)):
            self.Vectors = self.CornerTopRight
        
    def __init__(self, squad,  position, isCorner,priority, graph, defDirs):
        self.position = position
        self.isCorner = isCorner
        self.defenders = squad.bots
        self.squad = squad
        self.Vectors = defDirs
        self.assignDefenders(squad.bots)
        self.numAliveDefenders = len(squad.bots)
        self.priority = priority
        self.graph = graph
        
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        if isinstance(self.Vectors, list):
            if self.Vectors:
                splitVectors = list(chunks(self.Vectors, min(len(defenders), len(self.Vectors))))
                for i, bot in enumerate(defenders):
                    print "assigning", bot.name, splitVectors[(i+1)%len(splitVectors)]
                    bot.defending_direction = splitVectors[(i+1)%len(splitVectors)]
        else:
            for bot in defenders:
                bot.defending_direction = self.Vectors
            
    def reAssignRoles(self):
        aliveDefenders = filter(lambda x: x.health > 0, self.defenders)
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
            
    def execute(self):
        for defender in self.defenders:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority, self.graph))
                return
        aliveDefenders = [defender for defender in self.defenders if defender.health > 0]
        if len(aliveDefenders) != self.numAliveDefenders:
            self.numAliveDefenders = len(aliveDefenders)
            self.reAssignRoles()
        for defender in self.defenders:
            defender.update()      
    
    def enter(self):
        for defender in self.defenders:
            if not inArea(defender.position, self.position):
                print "Attack before Defend"
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority, self.graph))
                return
        
        for defender in self.defenders:
            defender.changeState(DefendingSomething(defender, defender.commander.level.findNearestFreePosition(self.position), priority=self.priority))           
    
    def exit(self):
        pass

class Scout():
    def __init__(self, squad, positions):
        self.squad = squad
        self.bots = squad.bots
        self.positions = positions
        self.numAlive = len(self.bots)
    
    def enter(self):
        for bot in self.bots:
            bot.changeState(AttackPostition(bot, random.choice(self.positions)))
    
    def execute(self):
        for bot in self.bots:
            if (bot.state == BotInfo.STATE_IDLE):
                bot.changeState(AttackPostition(bot, random.choice(self.positions)))
            else:
                bot.update()
                
    def exit(self):
        pass
    
class GetFlag():
    def __init__(self, squad, graph):
        self.squad = squad
        self.bots = squad.bots
        self.flagBearer = None
        self.weHaveFlag = False
        self.graph = graph
        self.paths = {}
        
    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width
        
    def sneak(self, bot, position):   
        srcIndex = self.getNodeIndex(bot.position)
        dstIndex = self.getNodeIndex(position)
        pathNodes = nx.shortest_path(self.graph, srcIndex, dstIndex, 'weight')
        pathLength = len(pathNodes)
        if pathLength > 0:
            path = [self.bots[0].commander.positions[p] for p in pathNodes if self.bots[0].commander.positions[p]]
            if len(path) > 0:
                orderPath = path[::10]
                orderPath.append(path[-1]) # take every 10th point including last point
                self.paths[bot] = orderPath    # store the path for visualization
    
    def enter(self):
        for bot in self.bots:
            self.sneak(bot, bot.commander.game.enemyTeam.flag.position)
            bot.changeState(ChargePosition(bot, self.paths[bot]))
    
    def execute(self):
        for bot in self.bots:
            if bot.flag:
                self.weHaveFlag = True
                self.flagBearer = bot
        if self.weHaveFlag and not reduce(lambda x,y:x or y, map(lambda x: x.flag, self.bots)):
            self.weHaveFlag = False
                    
        for bot in self.bots:
            if bot.state == BotInfo.STATE_IDLE:
                if self.weHaveFlag:
                        self.sneak(bot, bot.commander.game.team.flagScoreLocation)
                        bot.changeState(ChargePosition(bot, self.paths[bot]))
                else:
                    self.sneak(bot, bot.commander.game.enemyTeam.flag.position)
                    bot.changeState(ChargePosition(bot, self.paths[bot]))
            else:
                bot.update()
                
    def exit(self):
        pass