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
        if(self.bot.flag and self.bot.currState != ReturningFlag(self.bot)):
            self.bot.changeState(ReturningFlag(self.bot))
    
class DefendingSomething(State):
    
    def __init__(self, bot, position, priority =0):
        self.bot = bot
        self.position = position
        self.priority = priority
        
    def execute(self):
        aliveEnemies = filter(lambda x: x.health > 0, self.bot.visibleEnemies)
        if aliveEnemies:
            self.bot.changeState(DefendingAgainst(self.bot, self.bot.getClosestEnemy()))
        elif self.bot.defenceTrigger == 1:
            self.bot.defenceTrigger = 0
            print self.bot.defendingGroup.defenders[self.bot]
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.bot.defendingGroup.defenders[self.bot], description="Defending Position")
            
    def enter(self):
        if inArea(self.bot.position, self.position):
            if self.bot.defendingGroup:
                print self.bot.defendingGroup.defenders[self.bot]
                self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.bot.defendingGroup.defenders[self.bot], description="Defending Position")
        else:
            if self.priority == 1:
                self.bot.changeState(ChargePosition(self.bot, self.position))
            else:
                self.bot.changeState(AttackPostition(self.bot, self.position))
    
class DefendingAgainst(State):
    
    def __init__(self, bot, enemy):
        self.bot = bot
        self.enemy = enemy
    
    def execute(self):
        if self.enemy.health <= 0:
            self.bot.changeState(self.bot.prevState.pop())
        elif not inVOF(self.bot, self.enemy, self.bot.commander.level.FOVangle):
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.enemy.position - self.bot.position, description="Defending Against")
    
    def enter(self):
        self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.enemy.position - self.bot.position, description="Defending Against")
        pass

class AttackPostition(State):
    
    def __init__(self, bot, position):
        self.bot = bot
        self.position = position   
    
    def execute(self):
        aliveEnemies = filter(lambda x: x.health > 0, self.bot.visibleEnemies)
        if (len(aliveEnemies) > 1):
            self.bot.changeState(AvoidSomething(self.bot, map(lambda x:x.position, aliveEnemies)))
        elif (len(aliveEnemies) == 1):
            enemy = aliveEnemies[0]
            if(inVOF(enemy, self.bot, self.bot.commander.level.FOVangle) and distanceBetween(self.bot, enemy) > self.bot.commander.level.firingDistance + 2) or not inVOF(enemy, self.bot, self.bot.commander.level.FOVangle):
                self.bot.changeState(AttackingSomeone(self.bot, enemy))
        elif inArea(self.bot.position, self.position):           
            if self.bot.prevState:
                print "Going to prev"
                self.bot.changeState(self.bot.prevState.pop())
            else:
                self.bot.changeState(DefendingSomething(self.bot, self.position))
        elif self.bot.state == 1:
            self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.position, description="Attacking Position")
   
    def enter(self):
        self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.position, description="Attacking Position")

class ChargePosition(State):
    
    def __init__(self, bot, position):
        self.bot = bot
        self.position = position   
    
    def execute(self):
        aliveEnemies = filter(lambda x: x.health > 0, self.bot.visibleEnemies)
        if (len(aliveEnemies) > 1):
            self.bot.changeState(AvoidSomething(self.bot, map(lambda x:x.position, aliveEnemies)))
        elif (len(aliveEnemies) == 1):
            enemy = aliveEnemies[0]
            if(inVOF(enemy, self.bot, self.bot.commander.level.FOVangle) and distanceBetween(self.bot, enemy) > self.bot.commander.level.firingDistance + 2) or not inVOF(enemy, self.bot, self.bot.commander.level.FOVangle):
                self.bot.changeState(AttackingSomeone(self.bot, enemy))
        elif inArea(self.bot.position, self.position):           
            if self.bot.prevState:
                print "Going to prev"
                self.bot.changeState(self.bot.prevState.pop())
            else:
                self.bot.changeState(DefendingSomething(self.bot, self.position))
    
    def enter(self):
        self.bot.commander.issue(commands.Charge, self.bot, self.position)

class ReturningFlag(State):
    
    def execute(self):
        if not self.bot.flag:
            self.bot.changeState(self.bot.prevState.pop())
    
    def enter(self):
        self.bot.commander.issue(commands.Charge, self.bot, self.bot.commander.game.team.flag.position, description="Returning Flag")

class AttackingSomeone(State):   
    
    def __init__(self, bot, enemy):
        self.bot = bot
        self.enemy = enemy
        
    def execute(self):
        if (self.enemy.health <= 0):
            self.bot.changeState(self.bot.prevState.pop())
    
    def enter(self):
        self.bot.commander.issue(commands.Attack, self.bot, self.enemy.position, lookAt=self.enemy.position, description="Attacking Bot")

class AvoidSomething(State):
    
    def __init__(self, bot, listAvoiding):
        self.bot = bot
        self.avoiding = listAvoiding
    
    def execute(self):
        pass
    
    def enter(self):
        pass  

    
    
    