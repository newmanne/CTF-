from api import commands, vector2
from api import Commander
from util import *

from api.gameinfo import BotInfo, MatchCombatEvent


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
    
    def __init__(self, bot):
        self.bot = bot
        
    def execute(self):
        if self.bot:
            events = self.bot.commander.game.match.combatEvents
            events = [event for event in events if event not in self.bot.commander.events]            
            killingEvents = [event for event in events if event.type == MatchCombatEvent.TYPE_KILLED]
            for event in killingEvents:
                if event.instigator == self.bot.bot_info:
                    self.bot.score+=5
                    self.bot.commander.events.add(event)
                elif event.subject == self.bot.bot_info:
                    self.bot.score-=10
                    self.bot.commander.events.add(event)
            flagEvents = [event for event in events if event.type == MatchCombatEvent.TYPE_FLAG_CAPTURED or event.type == MatchCombatEvent.TYPE_FLAG_PICKEDUP]
            for event in flagEvents:
                if event.instigator == self.bot.bot_info:
                    self.bot.commander.events.add(event)
                    if event.type == MatchCombatEvent.TYPE_FLAG_CAPTURED:
                        self.bot.score+=200                       
                    else:
                        self.bot.score+=100

    
class DefendingSomething(State):
    
    def __init__(self, bot, position, priority =0, ticks=None):
        self.bot = bot
        self.position = position
        self.counter = ticks
        
    def execute(self):
        if self.bot.defenceTrigger == 1:
            self.bot.defenceTrigger = 0
            self.bot.commander.issue(commands.Defend, self.bot, facingDirection =self.bot.defending_direction, description="Defending Position")
        if self.counter:
            self.counter-=1
            if self.counter <= 0:
                self.bot.commander.issue(commands.Attack, self.bot, self.bot.position, description="Defending Position")
            
    def enter(self):
        self.bot.commander.issue(commands.Defend, self.bot, facingDirection = self.bot.defending_direction, description="Defending Position")

class DefendingAgainst(State):
    
    def __init__(self, bot, enemy, dontChange = False):
        self.bot = bot
        self.enemy = enemy
        self.dontChange = dontChange
    
    def execute(self):
        if (self.enemy.health <= 0 or self.enemy not in self.bot.visibleEnemies) and not self.dontChange:
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
        if self.bot.state == 1:
            self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.lookAt, description="Attacking Position")
   
    def enter(self):
        self.bot.commander.issue(commands.Attack, self.bot, self.position, lookAt=self.lookAt, description="Attacking Position")

class ChargePosition(State):
    
    def __init__(self, bot, position):
        self.bot = bot
        self.position = position   
    
    def execute(self):
        pass
    
    def enter(self):
        self.bot.commander.issue(commands.Charge, self.bot, self.position)