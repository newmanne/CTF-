from util import *
from api import Vector2
from states import *
import random
from api import Commander

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
            if self.defendingGroup:
                self.defendingGroup.reAssignRoles()
            self.currState.enter()
        elif self.health >0:
            self.globalState.execute()
            self.currState.execute()
        elif self.health <=0:
            self.currState = None
            self.prevState = []
    
    def changeState(self, state):
        self.prevState.append(self.currState)
        self.currState.exit()
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
    
class DefendingGroup():
    VectorOne = (Vector2(1.412, 1), 1)
    VectorTwo = (Vector2(-1.412, 1), 1)
    VectorThree = (Vector2(0, -1), 1)
    VectorFour = (Vector2(0, 1), 1)
    VectorFive = (Vector2(1.412, -1), 1)
    VectorSix = (Vector2(-1.412, -1), 1)
    Vectors = [VectorOne, VectorTwo, VectorThree, VectorFour, VectorFour, VectorFive, VectorSix]
    
    def assignVector(self, isCorner):
        if(isCorner == (0,0)):
            return
        elif(isCorner == (1,0)):
            self.Vectors = [(Vector2(1,0), 1),  (Vector2(1,1.412), 1), (Vector2(1,-1.412), 1)]
        elif(isCorner == (-1,0)):
            self.Vectors = [(Vector2(-1,0), 1), (Vector2(-1,1.412), 1), (Vector2(-1,-1.412), 1)]
        elif(isCorner == (0,1)):
            self.Vectors = [(Vector2(0,1), 1), (Vector2(1.412,1), 1), (Vector2(-1.412,1), 1)]
        elif(isCorner == (0,-1)):
            self.Vectors = [(Vector2(0,-1), 1), (Vector2(1.412,-1), 1), (Vector2(-1.412,-1), 1)]
        elif(isCorner == (1,1)):
            self.Vectors = [(Vector2(1.412,1), 1), (Vector2(1,1.412), 1)]
        elif(isCorner == (1,-1)):
            self.Vectors = [(Vector2(1.412,-1), 1), (Vector2(1,-1.412), 1)]
        elif(isCorner == (-1,1)):
            self.Vectors = [(Vector2(-1.412,1), 1), (Vector2(-1,1.412), 1)]
        elif(isCorner == (-1,-1)):
            self.Vectors = [(Vector2(-1.412,-1), 1), (Vector2(-1,-1.412), 1)]
        
    def __init__(self, bots, isCorner = (0,0)):
        self.assignVector(isCorner)
        self.defenders = {}
        self.assignDefenders(bots)
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        splitVectors = list(chunks(self.Vectors, len(defenders)))
        for i, bot in enumerate(defenders):
            self.defenders[bot] = splitVectors[i]
            
    def reAssignRoles(self):
        aliveDefenders = filter(lambda x: x.health > 0, self.defenders.keys())
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
