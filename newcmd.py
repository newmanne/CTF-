# Your AI for CTF must inherit from the base Commander class.  See how this is
# implemented by looking at the commander.py in the ./api/ folder.
from api import Commander
from api import gameinfo
# The commander can send 'Commands' to individual bots.  These are listed and
# documented in commands.py from the ./api/ folder also.
from api import commands

# The maps for CTF are layed out along the X and Z axis in space, but can be
# effectively be considered 2D.
from api import Vector2
import math
import sys
from api.gameinfo import BotInfo
from bot import Bot

def distance(vector1, vector2):
    return (vector1-vector2).length();

def distanceBetween(bot1, bot2):
    return distance(bot1.position, bot2.position)

class NewCommander(Commander):
    """
    Intelligence Objects
    """
    #enemies in radius:
    radius = 35.0
    closeEnemies = set()
    
    flagGone = False
    
    STATE_INITALIZING = 0
    STATE_DEFENDING = 1
    
    #Defender States
    HORIZONTAL = 0
    VERTICAL = 1

    """
    Rename and modify this class to create your own commander and add mycmd.Placeholder
    to the execution command you use to run the competition.
    """
    numOfDefWanted = 2
    currState = STATE_INITALIZING
    
    targetLeft = Vector2(-1.0, 0.0)
    targetAbove = Vector2(0.0, -1.0)
    targetBelow = Vector2(0.0, 1.0)
    
    defenders = {}
    
    def gatherIntel(self):
        self.closeEnemies = set()
        bots = self.game.bots_alive
        flagPosition = self.game.team.flag
        for bot in bots:
            for enemy in bot.visibleEnemies:
                if distanceBetween(enemy, flagPosition) < self.radius and enemy.health > 0:
                    self.closeEnemies.add(enemy)
        if self.game.team.flag.position != self.game.team.flagScoreLocation:
            self.flagGone = True
        else:
            self.flagGone = False
    
    
    def initialize(self):
        self.currState = self.STATE_INITALIZING
        

    def inArea(self, position, target):
        if distance(position, target) < 0.75:
            return True
        return False
    
    def inVOF(self, bot, enemy):
        facing = bot.facingDirection
        neededDir = enemy.position - bot.position
        cosTheta = (facing.x*neededDir.x + facing.y*neededDir.y)/(facing.length()*neededDir.length())
        if cosTheta >1:      
            cosTheta = 1
        if math.acos(cosTheta) <= self.level.FOVangle/2:
            return True
        return False
    
    def getClosestEnemy(self, bot):
        if len(bot.visibleEnemies) == 0:
            return None
        if len(bot.visibleEnemies) == 1:
            if bot.visibleEnemies[0].health > 0:
                return bot.visibleEnemies[0]
            else:
                return None
        enemy = reduce(lambda x,y: x if x.health > 0 and (x.position-bot.position).length() <= (y.position - bot.position).length() else y, bot.visibleEnemies)
        if enemy.health > 0:
            return enemy
        else:
            return None
    
    def findClosestDefender(self, enemy, defenders):
        if len(defenders)==0:
            return None;
        if len(defenders)==1:
            return defenders[0]
        return reduce(lambda x,y: x if distanceBetween(enemy, x[0]) <= distanceBetween(enemy, y[0]) else y, defenders)
    
    def initialSetup(self):
        self.defenders = {}
        for i, bot in enumerate(self.game.bots_alive):
            if len(self.defenders.values()) < self.numOfDefWanted:
                j = len(self.defenders.values())
                if j%2 == 0:
                    self.defenders[self.HORIZONTAL] = Bot(bot)
                else:
                    self.defenders[self.VERTICAL] = Bot(bot, defending_direction=Vector2(0, 1))
            else:
                #set up attack
                pass
        self.currState = self.STATE_DEFENDING
        
    def defensive(self):
        target = self.game.team.flag.position + self.targetLeft
        if len(self.defenders) < 2:
            self.initialSetup()
        enemiesNotTargeted = list(self.closeEnemies)
        for botKey in self.defenders.keys():
            botValues = self.defenders[botKey]
            if botValues.enemy_targeting and botValues.enemy_targeting in enemiesNotTargeted:
                enemiesNotTargeted.remove(botValues.enemy_targeting)
                    
        for i, botKey in enumerate(self.defenders.keys()):
            bot = self.defenders[botKey]
            bot_info = bot.bot_info
            if bot_info.health<=0:
                del self.defenders[botKey]
            elif enemiesNotTargeted and (not bot.enemy_targeting or bot.enemy_targeting.health <= 0):
                if not self.inArea(bot_info.position, target):
                    self.issue(commands.Charge, bot_info, target)
                else:
                    self.issue(commands.Defend, bot_info, facingDirection = enemiesNotTargeted[0].position - bot_info.position)
                    self.defenders[botKey] = Bot(bot_info=bot_info, defending_direction=bot.defending_direction, enemy_targeting=enemiesNotTargeted[0])
                    enemiesNotTargeted.remove(enemiesNotTargeted[0])
            else:
                if bot_info.state == BotInfo.STATE_IDLE:
                    if not self.inArea(bot_info.position, target):
                        self.issue(commands.Charge, bot_info, target)
                    else:
                        self.issue(commands.Defend, bot_info, facingDirection = [(bot.defending_direction, 1.5), (-bot.defending_direction, 1.5)])
                elif bot.enemy_targeting:
                    if bot.enemy_targeting.health<=0 or not bot.enemy_targeting in bot_info.visibleEnemies:
                        self.defenders[botKey] = Bot(bot_info=bot_info, defending_direction=bot.defending_direction)
                        if not self.inArea(bot_info.position, target):
                            self.issue(commands.Charge, bot_info, target)
                        else:
                            self.issue(commands.Defend, bot_info, facingDirection = [(bot.defending_direction, 1.5), (-bot.defending_direction, 1.5)])
                    elif not self.inVOF(bot_info, bot.enemy_targeting):
                        self.issue(commands.Defend, bot_info, facingDirection = bot_info.enemy_targeting.position - bot_info.position)                    
            
    
    def tick(self):
        self.gatherIntel()
        if self.currState == self.STATE_INITALIZING:
            self.initialSetup()
            self.defensive()
        elif self.currState == self.STATE_DEFENDING:
            self.defensive()
        else:
            raise ValueError
           
                            

    def shutdown(self):
        """Use this function to teardown your bot_info after the game is over, or perform an
        analysis of the data accumulated during the game."""

        pass
