import random

from api import Commander
from api import commands
from api.vector2 import Vector2


def contains(area, position):
    start, finish = area
    return position.x >= start.x and position.y >= start.y and position.x <= finish.x and position.y <= finish.y

class KilroyCommander(Commander):
    """
    see further documentation at http://code.google.com/p/sqlitebot/wiki/Kilroy
    """

    #FIX create per bot tick_command tracking vs the entire team 
    tick_command = 0
    tick_command_reset = 0
    lastEventCount = 0

    def initialize(self):
        self.attacker = None
        self.verbose = False


        # flanking setup from BalancedCommander
        # Calculate flag positions and store the middle.
        ours = self.game.team.flag.position
        theirs = self.game.enemyTeam.flag.position
        self.middle = (theirs + ours) / 2.0

        # Now figure out the flanking directions, assumed perpendicular.
        d = (ours - theirs)
        self.left = Vector2(-d.y, d.x).normalized()
        self.right = Vector2(d.y, -d.x).normalized()
        self.front = Vector2(d.x, d.y).normalized()

    def tick(self):

        #self.log.info('tick')
        enemyFlagLocation = self.game.enemyTeam.flag.position

        # TODO: When defender is down to the last bot that's attacking the flag, it'll end up ordering
        # the attacker to run all the way back from the flag to defend!
        if self.attacker and self.attacker.health <= 0:
            self.attacker = None

        #handle offense/attacker bot(s)
        for bot in self.game.bots_available:

            if (not self.attacker or self.attacker == bot) and len(self.game.bots_available) >= 1:
                self.attacker = bot

                if bot.flag:
                    #bring it home
                    targetLocation = self.game.team.flagScoreLocation
                    self.issue(commands.Charge, bot, targetLocation, description = 'returning enemy flag!')

                else:
                    target = self.game.enemyTeam.flag.position
                    flank = self.getFlankingPosition(bot, target)
                    if (target - flank).length() > (bot.position - target).length():
                        self.issue(commands.Attack, bot, target, description = 'attack from flank', lookAt=target)
                    else:
                        flank = self.level.findNearestFreePosition(flank)
                        self.issue(commands.Move, bot, flank, description = 'running to flank')


 

        ####

        #check combatEvents for latest activity
        if len(self.game.match.combatEvents) > self.lastEventCount:
            lastCombatEvent = self.game.match.combatEvents[-1]
            #self.log.info('event:'+str(lastCombatEvent.type))
            if lastCombatEvent.instigator is not None:
                print "event:%d %f %s %s" % (lastCombatEvent.type,lastCombatEvent.time,lastCombatEvent.instigator.name,lastCombatEvent.subject.name)
            else:
                print "event:%d %f" % (lastCombatEvent.type,lastCombatEvent.time)
            self.lastEventCount = len(self.game.match.combatEvents)

            #check for any nearby dead teammates to turn towards                
            if lastCombatEvent.type == 1 and (lastCombatEvent.subject.name.find(self.game.team.name) != -1):
                #face our last killed team member
                deadBot = self.game.bots[lastCombatEvent.subject.name]
                print "%s " % (deadBot.name)

                deadBotDefend = False   
                for bot in self.game.bots_alive:
                    if bot == self.attacker:
                        continue

                    if (deadBot.position - bot.position).length() < 20:
                        deadBotDefend = True    
                        print "%s defend deadBot" % (bot.name)
                        self.issue(commands.Defend, bot, (deadBot.position - bot.position), description = 'defending facing enemy bot')

                if deadBotDefend:
                    self.tick_command = self.game.match.timePassed+5

        ##
        enemyPosition = None
        closestEnemyDist = 1000

        for bot in self.game.bots_alive:
            if bot == self.attacker:
                continue

            #check for visible enemies
            #if bot.visibleEnemies != None:
            if len(bot.visibleEnemies) > 0:
                for visibleEnemy in bot.visibleEnemies:
                    if visibleEnemy.health > 0:
                        enemyDist = (visibleEnemy.position - bot.position).length() 
                        if enemyDist < closestEnemyDist:
                            closestEnemyDist = enemyDist
                            print "visibleEnemy:%s %f" % (visibleEnemy.name,enemyDist)
                            #self.log.info(bot.visibleEnemies)
                            #enemyPosition = bot.visibleEnemies[0].position             
                            enemyPosition = visibleEnemy.position

        if enemyPosition != None and self.game.match.timePassed > self.tick_command:
            self.tick_command = self.game.match.timePassed+5
            #self.log.info('tick_command:'+str(self.tick_command))

            #if nearby visible enemy, turn to face/defend
            for bot in self.game.bots_alive:
                if bot == self.attacker:
                    continue

                #if (enemyPosition - bot.position) != bot.facingDirection:
                if (enemyPosition - bot.position).length() < 30:
                    #self.log.info(enemyPosition-bot.position) 
                    #self.log.info(bot.facingDirection) 
                    print "%s defending visible bot" % (bot.name)
                    self.issue(commands.Defend, bot, (enemyPosition - bot.position), description = 'defending facing enemy bot')

        #periodically reset back to facing enemy flag 
        elif self.game.match.timePassed > self.tick_command and self.game.match.timePassed > self.tick_command_reset:
            self.tick_command_reset = self.game.match.timePassed+10
            for bot in self.game.bots_alive:
                if bot == self.attacker:
                    continue
                print "%s defending facing flag" % (bot.name)
                self.moveOrFace(bot)
                    
    ####
    
    #offense/attacker flanking
    def moveOrFace(self, bot):
        enemyFlagLocation = self.game.enemyTeam.flag.position

        # defend the flag!
        targetPosition = self.game.team.flagScoreLocation
        targetMin = targetPosition - Vector2(8.0, 8.0)
        targetMax = targetPosition + Vector2(8.0, 8.0)
        if bot.flag:
            #bring it hooome
            targetLocation = self.game.team.flagScoreLocation
            self.issue(commands.Charge, bot, targetLocation, description = 'returning enemy flag!')
        else:
            if (targetPosition - bot.position).length() > 9.0 and  (targetPosition - bot.position).length() > 3.0 :
                while True:
                    position = self.level.findRandomFreePositionInBox((targetMin,targetMax))
                    if position and (targetPosition - position).length() > 3.0:
                        #self.issue(commands.Move, bot, position, description = 'defending around flag')
                        self.issue(commands.Attack, bot, position, description = 'defending around flag',lookAt=enemyFlagLocation)
                        break
            else:
                self.issue(commands.Defend, bot, (enemyFlagLocation - bot.position), description = 'defending facing flag')

    def getFlankingPosition(self, bot, target):
        flanks = [target + f * 16.0 for f in [self.left, self.right]]
        options = map(lambda f: self.level.findNearestFreePosition(f), flanks)
        return sorted(options, key = lambda p: (bot.position - p).length())[0]