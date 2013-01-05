from util import *
from api import Vector2
from states import *
import random
from api import Commander
from squadstates import *

def enum(*sequential, **named):
    enums = dict(zip(sequential, range(len(sequential))), **named)
    reverse = dict((value, key) for key, value in enums.iteritems())
    enums['reverse_mapping'] = reverse
    return type('Enum', (), enums)

class Bot():
    ROLE_MOVING = 1
    ROLE_DEFENDING = 2
    
    def __init__(self, bot_info, commander=None):
        self.bot_info = bot_info
        self.enemy_targeting = None
        self.attacking_partner = None
        self.how_much_danger = 0
        self.defending_direction = None
        self.weHaveFlag = False
        self.spawnTrigger = 0
        self.defenceTrigger = 0
        self.enemyDefendTrigger = None
        self.commander = commander
        self.defendingGroup = None
        
        #State Logic
        self.currState = None
        self.prevState = []
        self.globalState = GlobalState(self)
        self.initalState = None
        
    def getClosestEnemy(self):
        aliveEnemies = filter(lambda x: x.health > 0, self.bot_info.visibleEnemies)
        return min(aliveEnemies, key=lambda enemy: distanceBetween(enemy, self.bot_info))
    
    def update(self):
        if not self.currState and self.health >0:
            self.currState = self.initalState
            self.currState.enter()
        elif self.health >0:            
            self.globalState.execute()
            if self.currState:
                self.currState.execute()
        elif self.health <=0:
            self.currState = None
            self.prevState = []
    
    def changeState(self, state):
        if self.currState:
            self.prevState.append(self.currState)
            self.currState.exit()
        if self.initalState == None:
            self.initalState = state
        self.currState = state
        self.currState.enter()
        
    def __getattr__(self, attr):
        # see if this object has attr
        # NOTE do not use hasattr, it goes into
        # infinite recurrsion
        if attr in self.__dict__:
            # this object has it
            return getattr(self, attr)
        # proxy to the wrapped object
        return getattr(self.bot_info, attr)

class Goal():
    ATTACK = 0
    DEFEND = 1
    PATROL = 2
    GETFLAG = 3
    GREED = 4
    def __init__(self, objective, position=None, isCorner=None, priority = 0, graph=None, dirs = None):
        self.objective = objective
        self.position = position
        self.isCorner = isCorner
        self.priority = priority
        self.graph = graph
        self.dirs = dirs
        
class Squad():
    def __init__(self,bots, goal, commander=None):
        self.bots = bots
        self.goal = goal
        if (self.goal.objective == Goal.ATTACK):
            self.initalState = Attack(self, goal.position, goal.isCorner, goal.priority, goal.graph)
        elif (self.goal.objective == Goal.DEFEND):
            self.initalState = Defend(self, goal.position, goal.isCorner, goal.priority, goal.graph, goal.dirs)
        elif (self.goal.objective == Goal.PATROL):
            self.initalState = Scout(self, goal.position)            
        elif (self.goal.objective == Goal.GETFLAG):
            self.initalState = GetFlag(self, goal.graph)
        elif (self.goal.objective == Goal.GREED):
            self.initalState = Greedy(self, commander)
        else:
            raise ValueError
        self.currState = None
        self.prevState = []
        
    def updateGraph(self, graph):
        if self.currState:
            self.currState.graph = graph
    
    def removeBot(self, bot):
        if bot in self.bots:
            self.bots.remove(bot)
            if bot in self.currState.bots:
                self.currState.bots.remove(bot)
            
    def addBot(self, bot):
        if bot not in self.bots:
            self.bots.append(bot)
            self.currState.bots.append(bot)
    
    def getRandomBot(self):
        if self.bots:
            return random.choice(self.bots)
        else:
            return None
    
    def update(self):
        if not self.currState:
            self.currState = self.initalState
            self.currState.enter()
        else:
            self.currState.execute()
        
    def changeState(self, state):
        if self.currState:
            self.prevState.append(self.currState)
            self.currState.exit()
        self.currState = state
        self.currState.enter()
        
class DefendingGroup():
    VectorOne = (Vector2(1.55, 1), 1)
    VectorTwo = (Vector2(-1.55, 1), 1)
    VectorThree = (Vector2(0, -1), 1)
    VectorFour = (Vector2(0, 1), 1)
    VectorFive = (Vector2(1.55, -1), 1)
    VectorSix = (Vector2(-1.55, -1), 1)
    Vectors = [VectorOne, VectorTwo, VectorThree, VectorFour, VectorFour, VectorFive, VectorSix]
    
    def assignVector(self, isCorner):
        if(isCorner == (0,0)):
            return
        elif(isCorner == (1,0)):
            self.Vectors = [(Vector2(1,0), 1),  (Vector2(1,1.55), 1), (Vector2(1,-1.55), 1)]
        elif(isCorner == (-1,0)):
            self.Vectors = [(Vector2(-1,0), 1), (Vector2(-1,1.55), 1), (Vector2(-1,-1.55), 1)]
        elif(isCorner == (0,1)):
            self.Vectors = [(Vector2(0,1), 1), (Vector2(1.55,1), 1), (Vector2(-1.55,1), 1)]
        elif(isCorner == (0,-1)):
            self.Vectors = [(Vector2(0,-1), 1), (Vector2(1.55,-1), 1), (Vector2(-1.55,-1), 1)]
        elif(isCorner == (1,1)):
            self.Vectors = [(Vector2(1.55,1), 1), (Vector2(1,1.55), 1)]
        elif(isCorner == (1,-1)):
            self.Vectors = [(Vector2(1.55,-1), 1), (Vector2(1,-1.55), 1)]
        elif(isCorner == (-1,1)):
            self.Vectors = [(Vector2(-1.55,1), 1), (Vector2(-1,1.55), 1)]
        elif(isCorner == (-1,-1)):
            self.Vectors = [(Vector2(-1.55,-1), 1), (Vector2(-1,-1.55), 1)]
        
    def __init__(self, bots, isCorner = (0,0)):
        self.assignVector(isCorner)
        self.bots = {}
        self.assignDefenders(bots)
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        splitVectors = list(chunks(self.Vectors, len(defenders)))
        for i, bot in enumerate(defenders):
            self.bots[bot] = splitVectors[i]
            
    def reAssignRoles(self):
        aliveDefenders = filter(lambda x: x.health > 0, self.bots.keys())
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
