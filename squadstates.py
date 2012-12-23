from api import Vector2
from util import *
from states import *
       
class Attack():
    def __init__(self, squad, position, isCorner, priority):
        self.squad = squad
        self.bots = squad.bots
        self.position = position
        self.isCorner = isCorner
        self.priority = priority
    
    def execute(self):
        arrived = map(lambda x: inArea(x.position, self.position), self.bots)
        arrived = reduce(lambda x,y:x and y, arrived)
        if arrived:
            self.squad.changeState(Defend(self.squad,  self.position, self.isCorner,self.priority))
        for bot in self.bots:
            bot.update()
    
    def enter(self):        
        for bot in self.bots:
            if(self.priority == 0):
                bot.changeState(AttackPostition(bot, bot.commander.level.findNearestFreePosition(self.position)))
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
        
    def __init__(self, squad,  position, isCorner,priority):
        self.position = position
        self.isCorner = isCorner
        self.assignVector()
        self.defenders = squad.bots
        self.squad = squad
        self.assignDefenders(squad.bots)
        self.numAliveDefenders = len(squad.bots)
        self.priority = priority
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        splitVectors = list(chunks(self.Vectors, min(len(defenders), len(self.Vectors))))
        for i, bot in enumerate(defenders):
            bot.defending_direction = splitVectors[(i+1)%len(splitVectors)]
            
    def reAssignRoles(self):
        aliveDefenders = filter(lambda x: x.health > 0, self.defenders)
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
            
    def execute(self):
        for defender in self.defenders:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority))
                return
        aliveDefenders = [defender for defender in self.defenders if defender.health > 0]
        if len(aliveDefenders) < self.numAliveDefenders:
            self.numAliveDefenders = len(aliveDefenders)
            self.reAssignRoles()
        for defender in self.defenders:
            defender.update()      
    
    def enter(self):
        for defender in self.defenders:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority))
                return
        
        for defender in self.defenders:
            defender.changeState(DefendingSomething(defender, defender.commander.level.findNearestFreePosition(self.position), priority=self.priority))           
    
    def exit(self):
        pass