from api import Vector2
from util import *
from states import *

import random

import networkx as nx
from api.gameinfo import BotInfo, MatchCombatEvent
import itertools

class Sneaky():
    def getNodeIndex(self, position):
        i = int(position.x)
        j = int(position.y)
        width = self.graph.graph["map_width"]
        return i+j*width
        
    def sneak(self, bot, position):   
        srcIndex = self.getNodeIndex(bot.position)
        dstIndex = self.getNodeIndex(position)
        try:
            pathNodes = nx.shortest_path(self.graph, srcIndex, dstIndex, 'weight')
            pathLength = len(pathNodes)
            if pathLength > 0:
                path = [self.bots[0].commander.positions[p] for p in pathNodes if self.bots[0].commander.positions[p]]
                if len(path) > 0:
                    orderPath = path[::10]
                    orderPath.append(path[-1]) # take every 10th point including last point
                    self.paths[bot] = orderPath    # store the path for visualization
        except:
            self.paths[bot] = position
       
class Attack(Sneaky):
    def __init__(self, squad, position, isCorner, priority, graph):
        self.squad = squad
        self.bots = squad.bots
        self.position = position
        self.isCorner = isCorner
        self.priority = priority
        self.graph = graph
        self.paths = {}
        self.deadBots = set()
        self.arrivedBots = set()
        
        
    def updateDeadBots(self):
        self.deadBots = filter(lambda x: x.health <= 0, self.deadBots)
        newDeadBots = [bot in bot for bot in self.bots if bot.health <=0 and bot not in self.bots]
        weightAdded = 10
        for bot in newDeadBots:
            node = bot.position
            rangeOf = list(range(-5, 6)) + list(range(-5, 6))            
            rangeOf = [x for x in rangeOf if x != 0]            
            surroundingNodes = set(itertools.permutations(rangeOf, 2))                  
            for i,j in surroundingNodes:
                if self.inZone(node + Vector2(i, j)):
                    if self.graph.has_edge(self.terrain[node.x][node.y], self.terrain[node.x+i][node.y+j]):
                        # we added this one before, just increase the weight by one
                        self.graph[self.terrain[node.x][node.y]][self.terrain[node.x+i][node.y+j]]['weight'] += weightAdded/math.hypot(i, j)   
    
    def execute(self):
        self.updateDeadBots()
        arrivedBots = (inArea(bot.position, self.position) for bot in self.bots)
        if all(arrivedBots):
            self.squad.changeState(self.squad.prevState.pop())
            return
        else:
            arrivedBots = filter(lambda x: inArea(x.position, self.position) and x not in self.arrivedBots, self.bots)
            self.arrivedBots = self.arrivedBots.union(set(arrivedBots))
            for bot in arrivedBots:
                bot.changeState(DefendingSomething(bot, bot.commander.level.findNearestFreePosition(self.position), priority=self.priority))           
        idleBots = (bot.state == BotInfo.STATE_IDLE for bot in self.bots)
        toBeRemoved = None
        if self.priority == 0 and all(idleBots):
            for bot in self.bots:
                if bot.flag:
                    bot.changeState(ChargePosition(bot, bot.commander.game.team.flagScoreLocation))
                    toBeRemoved = bot
                else:
                    self.sneak(bot, self.position)
                    bot.changeState(ChargePosition(bot, self.paths[bot]))
        else:
            for bot in self.bots:
                bot.update()
        if toBeRemoved:
            self.bots.remove(toBeRemoved)

    def enter(self):        
        for bot in self.bots:
            if self.priority == 0:
                self.sneak(bot, self.position)
                bot.changeState(ChargePosition(bot, self.paths[bot]))
            else:
                bot.changeState(ChargePosition(bot, bot.commander.level.findNearestFreePosition(self.position)))
    
    def exit(self):
        pass

class Defend():
        
    def __init__(self, squad,  position, isCorner,priority, graph, defDirs):
        self.position = position
        self.isCorner = isCorner
        self.bots = squad.bots
        self.squad = squad
        self.Vectors = set(defDirs)
        self.assignDefenders(squad.bots)
        self.numAliveDefenders = len(squad.bots)
        self.priority = priority
        self.graph = graph
        
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        if self.Vectors:
            splitVectors = list(chunks(list(self.Vectors), min(len(defenders), len(self.Vectors))))
            for i, bot in enumerate(defenders):
                bot.defending_direction = splitVectors[(i+1)%len(splitVectors)]
            
    def getAliveDefenders(self):
        return filter(lambda x: x.health > 0, self.bots)
    
    def getDeadDefenders(self):
        return (bot for bot in self.bots if bot.health <= 0)

    def reAssignRoles(self):
        aliveDefenders = self.getAliveDefenders()
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
        
    def updateDefendingDirections(self, aliveDefenders):
        if len(aliveDefenders) < self.numAliveDefenders:
            events = self.squad.commander.game.match.combatEvents
            killingEvents = (event for event in events for deadDefender in self.getDeadDefenders() if event.subject == deadDefender.bot_info and event.type == MatchCombatEvent.TYPE_KILLED)
            for killingEvent in killingEvents:
                if killingEvent.instigator.position and killingEvent.subject.position:
                    newVector = killingEvent.instigator.position - killingEvent.subject.position
                    if all(areUniqueAngles(newVector, b[0], 15) for b in self.Vectors):
                        self.Vectors.add((newVector, 1))
                    
        while len(self.Vectors) > max(len(self.bots) * 2, 3):
            self.Vectors.pop()
    
    def execute(self):
        for defender in self.bots:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority, self.graph))
                return
        aliveDefenders = [defender for defender in self.bots if defender.health > 0]
        if len(aliveDefenders) != self.numAliveDefenders:
            self.updateDefendingDirections(aliveDefenders)
            self.numAliveDefenders = len(aliveDefenders)
            self.reAssignRoles()
        for defender in self.bots:
            defender.update()
        
    def enter(self):
        for defender in self.bots:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority, self.graph))
                return
        
        for defender in self.bots:
            defender.changeState(DefendingSomething(defender, defender.commander.level.findNearestFreePosition(self.position), priority=self.priority))           
    
    def exit(self):
        pass

class Scout():
    def __init__(self, squad, positions):
        self.squad = squad
        self.bots = squad.bots
        self.positions = positions
        self.numAlive = len(self.bots)
        self.currentlyScouting = random.choice(self.positions)
        self.alertTicks = 10
        self.counter = self.alertTicks
        self.alert = False
        self.currentAttacker = None
        self.priorEvents = set()
    
    def enter(self):
        for bot in self.bots:
            bot.changeState(AttackPostition(bot, self.currentlyScouting))
            
    def getDeadScouts(self):
        return (bot for bot in self.bots if bot.health <= 0)
            
    def getKiller(self):
        events = self.squad.commander.game.match.combatEvents
        killingEvents = (event for event in events for deadScout in self.getDeadScouts() if event.subject == deadScout.bot_info and event.type == MatchCombatEvent.TYPE_KILLED)
        
        newKillingEvents = [killEvent for killEvent in killingEvents if killEvent not in self.priorEvents]
        if newKillingEvents:
            self.priorEvents = self.priorEvents.union(set(newKillingEvents))
            killingEvent = random.choice(newKillingEvents)
            if killingEvent.instigator.position:
                if not any(map(lambda x: inArea(x, killingEvent.instigator.position, 10), self.positions)):
                    self.positions.pop()
                    self.positions.append(killingEvent.instigator.position)
            return killingEvent.instigator
        else:
            return None
    
    def execute(self):
        attacker = self.getKiller()
        if attacker or (self.alert and self.currentAttacker):
            if not self.alert:
                self.alert = True
                self.currentAttacker = attacker
                for bot in self.bots:
                    if not inVOF(bot, attacker, self.squad.commander.level.fieldOfViewAngles[bot.state]):
                        bot.changeState(DefendingAgainst(bot, attacker, True))
                    else:
                        bot.update()
            elif self.counter!=0:
                self.counter-=1
                for bot in self.bots:
                    bot.update()
            elif self.counter == 0:
                self.alert = False
                self.currentAttacker = None
                self.counter = self.alertTicks
                for bot in self.bots:
                    bot.changeState(AttackPostition(bot, self.currentlyScouting))
                
        else:
            idle = all(map(lambda x: inArea(x.position, self.currentlyScouting), self.bots))
            if idle:
                self.currentlyScouting = random.choice(self.positions)
            for bot in self.bots:
                if idle:
                    bot.changeState(AttackPostition(bot, self.currentlyScouting))
                else:
                    bot.update()
                
    def exit(self):
        pass
    
class GetFlag(Sneaky):
    def __init__(self, squad, graph):
        self.squad = squad
        self.bots = squad.bots
        self.flagBearer = None
        self.weHaveFlag = False
        self.graph = graph
        self.paths = {}
    
    def enter(self):
        for bot in self.bots:
            self.sneak(bot, bot.commander.game.enemyTeam.flag.position)
            bot.changeState(ChargePosition(bot, self.paths[bot]))
    
    def execute(self):

        self.weHaveFlag = any(map(lambda x: x.flag, self.bots))
        if not self.weHaveFlag:
            self.flagBearer = None
        for bot in self.bots:
            if bot.state == BotInfo.STATE_IDLE or (not self.flagBearer and self.weHaveFlag and bot.flag):
                if self.weHaveFlag:
                    if bot.flag:
                        self.flagBearer = bot
                        self.sneak(bot, bot.commander.game.team.flagScoreLocation)
                        bot.changeState(ChargePosition(bot, self.paths[bot]))
                    else:
                        if bot.state != BotInfo.STATE_TAKINGORDERS:
                            self.sneak(bot, bot.commander.game.enemyTeam.flagSpawnLocation)
                            bot.changeState(ChargePosition(bot, self.paths[bot]))
                else:
                    self.sneak(bot, bot.commander.game.enemyTeam.flag.position)
                    bot.changeState(ChargePosition(bot, self.paths[bot]))
            else:
                bot.update()
                
    def exit(self):
        pass