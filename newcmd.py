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
import time

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
    STATE_ATTACKING = 2
    STATE_NEUTRAL = 3

    """
    Rename and modify this class to create your own commander and add mycmd.Placeholder
    to the execution command you use to run the competition.
    """
    numOfDefWanted = 2
    currState = STATE_INITALIZING
    
    targetLeft = Vector2(-1.0, 0.0)
    targetAbove = Vector2(0.0, -1.0)
    targetBelow = Vector2(0.0, 1.0)
    

    up = Vector2(0,1)
    left = Vector2(1,0)
    
    facingDirs = [up, left, -up, -left]
    
    defenders = {}
    attackers = set()
    
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
        bots = self.game.bots_alive
        for i, bot in enumerate(sorted(bots, key=lambda x: distanceBetween(x, self.game.team.flag))):
            if len(self.defenders.values()) < self.numOfDefWanted:
                j = len(self.defenders.values())
                if j%2 == 0:
                    self.defenders[j] = Bot(bot)
                else:
                    self.defenders[j] = Bot(bot, defending_direction=Vector2(0, 1))
            else:
                self.attackers.add(Bot(bot))
        self.currState = self.STATE_NEUTRAL
        
    def defend(self):
        target = self.game.team.flag.position + self.targetLeft
        if len(self.defenders) != self.numOfDefWanted:
            self.initialSetup()
        enemiesNotTargeted = list(self.closeEnemies)
        for botKey in self.defenders.keys():
            bot = self.defenders[botKey]
            if bot.enemy_targeting and bot.enemy_targeting in enemiesNotTargeted:
                enemiesNotTargeted.remove(bot.enemy_targeting)
                    
        for i, botKey in enumerate(self.defenders.keys()):
            bot = self.defenders[botKey]
            if bot.health<=0:
                del self.defenders[botKey]
            elif enemiesNotTargeted and (not bot.enemy_targeting or bot.enemy_targeting.health <= 0):
                self.issue(commands.Defend, bot, facingDirection = enemiesNotTargeted[0].position - bot.position)
                self.defenders[botKey] = Bot(bot_info=bot.bot_info, defending_direction=bot.defending_direction, enemy_targeting=enemiesNotTargeted[0])
                enemiesNotTargeted.remove(enemiesNotTargeted[0])
            else:
                if bot.state == BotInfo.STATE_IDLE:
                    if not self.inArea(bot.position, target):
                        self.issue(commands.Charge, bot, target)
                    else:
                        self.issue(commands.Defend, bot, facingDirection = [(bot.defending_direction, 1), (-bot.defending_direction, 1)])
                if bot.enemy_targeting:
                    if bot.enemy_targeting.health<=0:
                        self.defenders[botKey] = Bot(bot_info=bot.bot_info, defending_direction=bot.defending_direction)
                        if not self.inArea(bot.position, target):
                            self.issue(commands.Charge, bot, target)
                        else:
                            self.issue(commands.Defend, bot, facingDirection = [(bot.defending_direction, 1), (-bot.defending_direction, 1)])
                    elif not self.inVOF(bot, bot.enemy_targeting):
                        self.issue(commands.Defend, bot, facingDirection = bot.enemy_targeting.position - bot.position)                            
    
    def attack(self):
        weHaveFlag = map(lambda x: 1 if x.flag else 0, self.attackers)
        weHaveFlag = 1 in weHaveFlag
        for bot in self.attackers.copy():
            if bot.health <= 0:
                self.attackers.remove(bot)
            else:
                if bot.enemy_targeting and (bot.enemy_targeting.health <= 0 or distanceBetween(bot, bot.enemy_targeting) > 30):
                    bot.enemy_targeting = None
                    self.issue(commands.Attack, bot, self.game.enemyTeam.flag.position, lookAt = self.game.enemyTeam.flag.position)
        if weHaveFlag == True:
            for bot in self.attackers:
                if bot.weHaveFlag == 0:
                    bot.weHaveFlag = 1
                    aliveVisibleEnemies = filter(lambda x: x.health > 0, bot.visibleEnemies)
                    if bot.flag and not aliveVisibleEnemies:
                        self.issue(commands.Charge, bot, self.game.team.flagScoreLocation)
                    else:
                        self.issue(commands.Attack, bot, self.game.team.flagScoreLocation, lookAt = -self.game.team.flagScoreLocation)
        else:
            for i, bot in enumerate(self.attackers):
                aliveVisibleEnemies = filter(lambda x: x.health > 0, bot.visibleEnemies)
                if (bot.state == BotInfo.STATE_IDLE or bot.weHaveFlag == 1) or (not bot.enemy_targeting and aliveVisibleEnemies):
                    bot.weHaveFlag = 0
                    if aliveVisibleEnemies and distanceBetween(bot, bot.getClosestEnemy()) < 30:
                        bot.enemy_targeting = bot.getClosestEnemy()
                        self.issue(commands.Attack, bot, self.game.enemyTeam.flag.position, lookAt = bot.enemy_targeting.position)
                    else:                        
                        self.issue(commands.Attack, bot, self.game.enemyTeam.flag.position, lookAt = self.game.enemyTeam.flag.position)

    
    def tick(self):
        self.gatherIntel()
        if self.currState == self.STATE_INITALIZING:
            self.initialSetup()            
        elif self.currState == self.STATE_DEFENDING:
            self.numOfDefWanted=3
        elif self.currState == self.STATE_ATTACKING:
            self.numOfDefWanted=1
        elif self.currState == self.STATE_NEUTRAL:
            self.numOfDefWanted=2
        else:
            raise ValueError
        
        self.defend()
        self.attack()
        if self.game.bots_available:
            self.initialSetup()                    

    def shutdown(self):
        """Use this function to teardown your bot_info after the game is over, or perform an
        analysis of the data accumulated during the game."""

        pass
    
class PlaceholderCommander(Commander):
    """
    Rename and modify this class to create your own commander and add mycmd.Placeholder
    to the execution command you use to run the competition.
    """
    up = Vector2(0,1)
    left = Vector2(1,0)
    
    directions = (up, left, -up, -left)

    def initialize(self):
        """Use this function to setup your bot before the game starts."""
        self.verbose = True    # display the command descriptions next to the bot labels
        self.attackers = set()
        self.flagBearers = set()
        self.fulltimeToRespawn = self.game.match.timeToNextRespawn
        
        # Calculate flag positions and store the middle.
        ours = self.game.team.flagScoreLocation
        theirs = self.game.enemyTeam.flagScoreLocation
        self.middle = (theirs + ours) / 2.0

        # Now figure out the flaking directions, assumed perpendicular.
        d = (ours - theirs)
        self.left = Vector2(-d.y, d.x).normalized()
        self.right = Vector2(d.y, -d.x).normalized()
        self.front = Vector2(d.x, d.y).normalized()
        
        self.lastNumOfAttackers = 0
        
        self.numOfBotsInital = len(self.game.bots_alive)
        self.maxDefenders = self.numOfBotsInital -1
        self.attackersLast = self.maxDefenders
        numOfBotsAlive = len(self.game.bots_alive)
        # for all bots which aren't currently doing anything
        for bot in self.game.bots_available:
            if len(self.attackers) < self.maxDefenders:
                self.attackers.add(Bot(bot))
            else:
                self.flagBearers.add(Bot(bot))
    
    
    def inArea(self, position, target):
        if distance(position, target) < 0.75:
            return True
        return False

    def tick(self):
        """Override this function for your own bots.  Here you can access all the information in self.game,
        which includes game information, and self.level which includes information about the level."""
        
        numOfBotsAlive = len(self.game.bots_alive)
        
        aliveAttackers = filter(lambda x: x.health > 0, self.attackers)
        aliveFlaggers = filter(lambda x: x.health > 0, self.flagBearers)
        if not aliveFlaggers:
            for flaggers in self.flagBearers:
                self.attackers.add(flaggers)
            self.flagBearers.clear()
            if aliveAttackers:
                flagBearer = aliveAttackers[0]
                self.attackers.remove(aliveAttackers[0])
                self.flagBearers.add(flagBearer)
        
        weHaveFlag = map(lambda x: 1 if x.flag else 0, self.flagBearers)
        weHaveFlag = 1 in weHaveFlag
        for flagBearer in self.flagBearers:
            aliveEnemies = filter(lambda x: x.health > 0, flagBearer.visibleEnemies)
            enemyFlag = self.game.enemyTeam.flag.position
            if flagBearer.state == BotInfo.STATE_IDLE or (flagBearer.state == BotInfo.STATE_DEFENDING and flagBearer.flag) or (flagBearer.enemyDefendTrigger and flagBearer.enemyDefendTrigger.health <=0):
                if weHaveFlag:
                    if flagBearer.flag:
                        target = self.game.team.flagScoreLocation
                        self.issue(commands.Charge, flagBearer, target)
                    else:
                        if self.inArea(flagBearer.position, self.game.team.flagScoreLocation):
                            if self.attackers:
                                newFlagBearer = self.attackers.pop()
                                self.flagBearers.add(newAttacker)
                            self.flagBearers.remove(flagBearer)
                            self.attackers.add(flagBearer)
                        elif not self.inArea(flagBearer.position, enemyFlag):
                            self.issue(commands.Attack, flagBearer, enemyFlag, lookAt=enemyFlag,description = 'Run to enemy flag')                            
                else:
                    if not aliveEnemies:
                        self.issue(commands.Attack, flagBearer, enemyFlag, lookAt=enemyFlag,description = 'Run to enemy flag')
                    else:
                        self.smartAttack(flagBearer, enemyFlag)
                    
        enemyFlagScore = self.game.enemyTeam.flagScoreLocation
        aliveAttackers = filter(lambda x: x.health > 0, self.attackers)
        
        
        for i, attacker in enumerate(aliveAttackers):
            aliveEnemies = filter(lambda x: x.health > 0, attacker.visibleEnemies)
            if attacker.flag:
                if self.flagBearers:
                    newAttacker = self.flagBearers.pop()
                    self.attackers.add(newAttacker)
                self.attackers.remove(attacker)
                self.flagBearers.add(attacker)
                continue        
            elif attacker.state == BotInfo.STATE_IDLE or attacker.enemyDefendTrigger:
                if not self.inArea(attacker.position, enemyFlagScore + self.directions[i%4]):
                    attacker.role= Bot.ROLE_MOVING
                    target = enemyFlagScore + self.directions[i%4]
                    flank = self.getFlankingPosition(attacker, target)
                    if (target - flank).length() > (attacker.position - target).length() or i%2 == 1:
                        if not aliveEnemies:
                            self.issue(commands.Attack,attacker, target ,lookAt=target)
                        else:
                            self.smartAttack(attacker, target)
                    else:
                        flank = self.level.findNearestFreePosition(flank)
                        if not aliveEnemies:
                            self.issue(commands.Charge ,attacker, flank)
                        else:
                            self.smartAttack(attacker, target)
                else:
                    attacker.role = Bot.ROLE_DEFENDING
                    
        aliveDefenders = filter(lambda x: x.health > 0 and x.role == Bot.ROLE_DEFENDING, self.attackers)
        numOfAttackers = len(aliveDefenders)
        if numOfAttackers < self.lastNumOfAttackers:
            self.lastNumOfAttackers = numOfAttackers
            for attacker in aliveAttackers:
                if attacker.role==Bot.ROLE_DEFENDING and attacker.spawnTrigger != 1:
                    attacker.defenceTrigger = 0        
        for i, attacker in enumerate(aliveDefenders):
            if attacker.spawnTrigger == 1 and self.game.match.timeToNextRespawn > 5 and self.game.match.timeToNextRespawn <  self.fulltimeToRespawn - 3 and not attacker.visibleEnemies:
                attacker.spawnTrigger = 0
                attacker.defenceTrigger = 0
            if self.game.match.timeToNextRespawn < 5 and attacker.spawnTrigger == 0:
                attacker.spawnTrigger = 1
                attacker.defenceTrigger = -1
                self.issue(commands.Defend, attacker, facingDirection=self.level.findRandomFreePositionInBox(self.game.enemyTeam.botSpawnArea) - attacker.position)
            elif attacker.defenceTrigger == 0:
                attacker.defenceTrigger = 1
                if numOfAttackers == 1:
                    self.issue(commands.Defend, attacker, facingDirection=[(self.directions[0], 1), (self.directions[1], 1), (self.directions[2], 1), (self.directions[3], 1)])
                elif numOfAttackers == 2:
                    if i == 0:
                        self.issue(commands.Defend, attacker, facingDirection=[(self.directions[0], 1), (self.directions[2], 1)])
                    elif i == 1:
                        self.issue(commands.Defend, attacker, facingDirection=[(self.directions[1], 1), (self.directions[3], 1)])
                elif numOfAttackers == 3:
                    if i == 0:
                        self.issue(commands.Defend, attacker, facingDirection=self.directions[1])
                    elif i == 1:
                        self.issue(commands.Defend, attacker, facingDirection=self.directions[3])
                    elif i == 2:
                        self.issue(commands.Defend, attacker, facingDirection=[(self.directions[0], 1), (self.directions[2], 1)])
                else:
                    self.issue(commands.Defend, attacker, facingDirection=self.directions[i%4])
    def inVOF(self, bot, enemy):
        facing = bot.facingDirection
        neededDir = enemy.position - bot.position
        cosTheta = (facing.x*neededDir.x + facing.y*neededDir.y)/(facing.length()*neededDir.length())
        if cosTheta >1:      
            cosTheta = 1
        if math.acos(cosTheta) <= self.level.FOVangle/2:
            return True
        return False
    
    def smartAttack(self, bot, aim):
        aliveEnemies = filter(lambda x: x.health > 0, bot.visibleEnemies)
        mainEnemy = bot.getClosestEnemy()
        for enemy in aliveEnemies:
            if self.inVOF( enemy, bot) and distanceBetween(bot, mainEnemy) < self.level.firingDistance:
                self.issue(commands.Attack, bot,aim, lookAt=enemy.position)
                return
        if not bot.enemyDefendTrigger:
            bot.enemyDefendTrigger = mainEnemy
            self.issue(commands.Defend, bot, facingDirection= mainEnemy.position - bot.position)
        elif not bot.enemyDefendTrigger in bot.visibleEnemies:
            bot.enemyDefendTrigger = None
            self.issue(commands.Attack, bot,aim, lookAt=enemy.position)

            
#            bot.enemyDefendTrigger = mainEnemy
#            ours = bot.position
#            theirs = mainEnemy.position
#            middle = (theirs + ours) / 2.0
#    
#            # Now figure out the flaking directions, assumed perpendicular.
#            d = (ours - theirs)
#            self.left = Vector2(-d.y, d.x).normalized()
#            self.right = Vector2(d.y, -d.x).normalized()
#            self.front = Vector2(d.x, d.y).normalized()
#            target = theirs
#            flank = self.getFlankingPosition(bot,  target)
#            if (target - flank).length() > (bot.position - target).length():
#                self.issue(commands.Attack,bot, target ,lookAt=target)
#            else:
#                flank = self.level.findNearestFreePosition(flank)
#                self.issue(commands.Attack, bot,flank, lookAt=target)
            

            
                    
    def getFlankingPosition(self, bot, target):
        flanks = [target + f * 16.0 for f in [self.left, self.right]]
        options = map(lambda f: self.level.findNearestFreePosition(f), flanks)
        return sorted(options, key = lambda p: (bot.position - p).length())[0]

    def shutdown(self):
        """Use this function to teardown your bot after the game is over, or perform an
        analysis of the data accumulated during the game."""

        pass
