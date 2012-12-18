# Your AI for CTF must inherit from the base Commander class.  See how this is
# implemented by looking at the commander.py in the ./api/ folder.
from api import Commander
import random

# The maps for CTF are layed out along the X and Z axis in space, but can be
# effectively be considered 2D.
from api import Vector2
from bot import Bot, DefendingGroup
from states import  *


class FSMCommander(Commander):
    numOfAttackers = 2
    numOfDefenders = 2
    edgeDistance = 10
    
    def tick(self):
        aliveAttackers = filter(lambda x: x.health > 0, self.attackers)
        if len(aliveAttackers) != self.numOfAttackers:
            self.numOfAttackers = len(aliveAttackers)
            self.attackingGroup.reAssignRoles()
            
        aliveDefenders = filter(lambda x: x.health > 0, self.defenders)
        if len(aliveDefenders) != self.numOfDefenders:
            self.numOfDefenders = len(aliveDefenders)
            self.defendingGroup.reAssignRoles()
        
        num = len(self.bots)
        bots = list(self.bots)
        for bot in self.bots:
            bot.update()
            
    def isNearEdge(self, xory, position):
        if xory==0:
            return self.level.width - position.x < self.edgeDistance or position.x < self.edgeDistance
        else:
            return self.level.height - position.y < self.edgeDistance or position.y < self.edgeDistance

    def getStrategicPostion(self, position):
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
    
    def initialize(self):
        self.verbose = True
        self.bots = set()
        self.defenders = []
        self.attackers = []
        teamPosition, isTeamCorner = self.getStrategicPostion(self.game.team.flag.position)
        enemyPosition, isEnemyCorner = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        for bot_info in self.game.bots_available:
            bot = Bot(bot_info, self)
            self.bots.add(bot)
            if len(self.defenders) < self.numOfDefenders:                
                bot.initalState = DefendingSomething(bot, self.level.findNearestFreePosition(teamPosition), priority=1)                
                self.defenders.append(bot)    
            elif len(self.attackers) < self.numOfAttackers:
                bot.initalState = DefendingSomething(bot, self.level.findNearestFreePosition(enemyPosition))                
                self.attackers.append(bot)            
            else:
                bot.initalState = AttackPostition(bot, self.game.enemyTeam.flag.position)
                
        self.defendingGroup = DefendingGroup(self.defenders, isTeamCorner)
        self.attackingGroup = DefendingGroup(self.attackers, isEnemyCorner)
        for bot in self.defenders:
            bot.defendingGroup = self.defendingGroup
        for bot in self.attackers:
            bot.defendingGroup = self.attackingGroup