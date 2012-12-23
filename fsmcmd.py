# Your AI for CTF must inherit from the base Commander class.  See how this is
# implemented by looking at the commander.py in the ./api/ folder.
from api import Commander
import random

# The maps for CTF are layed out along the X and Z axis in space, but can be
# effectively be considered 2D.
from api import Vector2
from bot import Bot, DefendingGroup, Squad, Goal
from states import  *


class FSMCommander(Commander):
    numOfAttackers = 2
    numOfDefenders = 2
    edgeDistance = 10
    
    def tick(self):
      
        bots = list(self.bots)
        for squad in self.squads:
            squad.update()
        for bot in bots:
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
        teamPosition = self.level.findNearestFreePosition(teamPosition)
        enemyPosition, isEnemyCorner = self.getStrategicPostion(self.game.enemyTeam.flagScoreLocation)
        enemyPosition = self.level.findNearestFreePosition(enemyPosition)
        for i, bot_info in enumerate(self.game.bots_available):
            bot = Bot(bot_info, self)
            if len(self.defenders) < self.numOfDefenders:                
                self.defenders.append(bot)    
            elif len(self.attackers) < self.numOfAttackers:
                self.attackers.append(bot)
            elif (i%2) == 0:
                self.attackers.append(bot) 
            else:
                self.defenders.append(bot) 
                
        self.defendingGroup = Squad(self.defenders, Goal(Goal.DEFEND, teamPosition, isTeamCorner, priority=1))
        self.attackingGroup = Squad(self.attackers, Goal(Goal.DEFEND, enemyPosition, isEnemyCorner))
        
        self.squads = [self.defendingGroup, self.attackingGroup]