from api import commands
from api import Commander
from util import *



class State(object):
    '''
    Abstract state class
    '''
    def __init__(self, bot):
        self.bot = bot
        pass
    
    def execute(self):
        pass
    
    def enter(self):
        pass
    
    def exit(self):
        pass
    
class GlobalState(State):
    
    #Check if you have flag
    #Gather List Enemies/Friendlies
    def execute(self):
        pass
    
class DefendingSomething(State):
    
    def __init__(self, bot, position, priority =0):
        self.bot = bot
        self.position = position
        self.priority = priority
        
    def execute(self):
        aliveEnemies = [enemy for enemy in self.bot.visibleEnemies if enemy.health > 0]
        if aliveEnemies:
            if any(map(lambda x: inVOF(self.bot, x, self.bot.commander.level.fieldOfViewAngles[2]),  aliveEnemies)):
                self.bot.changeState(DefendingAgainst(self.bot, self.bot.getClosestEnemy()))
        if self.bot.defenceTrigger == 1:
            self.bot.defenceTrigger = 0
            #self.bot.facingDirection = self.bot.defending_direction
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection =self.bot.defending_direction, description="Defending Position")
            
    def enter(self):
        if inArea(self.bot.position, self.position):
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.bot.defending_direction, description="Defending Position")
    
class DefendingAgainst(State):
    
    def __init__(self, bot, enemy):
        self.bot = bot
        self.enemy = enemy
    
    def execute(self):
        if (self.enemy.health <= 0 or self.enemy not in self.bot.visibleEnemies):
            self.bot.changeState(self.bot.prevState.pop())
        elif not inVOF(self.bot, self.enemy, self.bot.commander.level.fieldOfViewAngles[2]):
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.enemy.position - self.bot.position, description="Defending Against")
    
    def enter(self):
        if not inVOF(self.bot, self.enemy,  self.bot.commander.level.fieldOfViewAngles[2]):
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.enemy.position - self.bot.position, description="Defending Against")

class AttackPostition(State):
    
    def __init__(self, bot, position, lookAt=None):
        self.bot = bot
        self.position = position
        if  (isinstance(self.position, list)):
            self.lookAt = None
        else:
            self.lookAt = lookAt
    
    def execute(self):
        aliveEnemies = filter(lambda x: x.health > 0, self.bot.visibleEnemies)
        if (len(aliveEnemies) > 1):
            self.bot.changeState(AvoidSomething(self.bot, map(lambda x:x.position, aliveEnemies)))
        elif (len(aliveEnemies) == 1):
            enemy = aliveEnemies[0]
            if distanceBetween(self.bot, enemy) > self.bot.commander.level.firingDistance + 2:
                self.bot.changeState(AttackingSomeone(self.bot, enemy))
        elif self.bot.state == 1:
            self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.lookAt, description="Attacking Position")
   
    def enter(self):
        self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.lookAt, description="Attacking Position")

class ChargePosition(State):
    
    def __init__(self, bot, position):
        self.bot = bot
        self.position = position   
    
    def execute(self):
        pass
#        aliveEnemies = filter(lambda x: x.health > 0, self.bot.visibleEnemies)
#        if (len(aliveEnemies) > 1):
#            self.bot.changeState(AvoidSomething(self.bot, map(lambda x:x.position, aliveEnemies)))
#        elif (len(aliveEnemies) == 1):
#            enemy = aliveEnemies[0]
#            if(inVOF(enemy, self.bot,  self.bot.commander.level.fieldOfViewAngles[5]) and distanceBetween(self.bot, enemy) > self.bot.commander.level.firingDistance + 2) or not inVOF(enemy, self.bot,  self.bot.commander.level.fieldOfViewAngles[5]):
#                self.bot.changeState(AttackingSomeone(self.bot, enemy))
    
    def enter(self):
        self.bot.commander.issue(commands.Charge, self.bot, self.position)

class ReturningFlag(State):
    
    def execute(self):
        if not self.bot.flag:
            self.bot.weHaveFlag = False
            self.bot.changeState(self.bot.prevState.pop())
    
    def enter(self):
        self.bot.weHaveFlag = True
        self.bot.commander.issue(commands.Charge, self.bot, self.bot.commander.game.team.flagScoreLocation, description="Returning Flag")

class AttackingSomeone(State):   
    
    def __init__(self, bot, enemy):
        self.bot = bot
        self.enemy = enemy
        
    def execute(self):
        if (self.enemy.health <= 0 or self.enemy not in self.bot.visibleEnemies):
            self.bot.changeState(self.bot.prevState.pop())
        elif not inAreaParameter(self.seenPosition, self.enemy.position, 5):
            self.seenPosition = self.enemy.position
            self.bot.commander.issue(commands.Attack, self.bot, self.enemy.position, lookAt=self.enemy.position, description="Attacking Bot")
    
    def enter(self):
        self.seenPosition = self.enemy.position
        self.bot.commander.issue(commands.Attack, self.bot, self.enemy.position, lookAt=self.enemy.position, description="Attacking Bot")

class AvoidSomething(State):
    
    def __init__(self, bot, listAvoiding):
        self.bot = bot
        self.avoiding = listAvoiding
    
    def execute(self):
        pass
    
    def enter(self):
        pass  

    
    
    