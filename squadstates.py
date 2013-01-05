from api import Vector2
from util import *
from states import *

import random

import networkx as nx
from api.gameinfo import BotInfo

class Greedy():
    def __init__(self, squad, commander):
        self.squad = squad
        self.bots = squad.bots
        self.commander = commander
    
    def captured(self):
        """Did this team cature the enemy flag?"""
        return self.commander.game.enemyTeam.flag.carrier != None
    
    def execute(self):
        """Process the bots that are waiting for orders, either send them all to attack or all to defend."""
        captured = self.captured()

        our_flag = self.commander.game.team.flag.position
        their_flag = self.commander.game.enemyTeam.flag.position
        their_base = self.commander.level.botSpawnAreas[self.commander.game.enemyTeam.name][0]

        # First process bots that are done with their orders...
        for bot in self.commander.game.bots_available:

            # If this team has captured the flag, then tell this bot...
            if captured:
                target = self.commander.game.team.flagScoreLocation
                # 1) Either run home, if this bot is the carrier or otherwise randomly.
                if bot.flag is not None or (random.choice([True, False]) and (target - bot.position).length() > 8.0):
                    self.commander.issue(commands.Charge, bot, target, description = 'scrambling home')
                # 2) Run to the exact flag location, effectively escorting the carrier.
                else:
                    self.commander.issue(commands.Attack, bot, self.commander.game.enemyTeam.flag.position, description = 'defending flag carrier',
                               lookAt = random.choice([their_flag, our_flag, their_flag, their_base]))

            # In this case, the flag has not been captured yet so have this bot attack it!
            else:
                path = [self.commander.game.enemyTeam.flag.position]
                if contains(self.commander.level.botSpawnAreas[self.commander.game.team.name], bot.position) and random.choice([True, False]):
                    path.insert(0, self.commander.game.team.flagScoreLocation)
                self.commander.issue(commands.Attack, bot, path, description = 'attacking enemy flag',
                                lookAt = random.choice([their_flag, our_flag, their_flag, their_base]))

        # Second process bots that are in a holding attack pattern.
        holding = len(self.commander.game.bots_holding)
        for bot in self.commander.game.bots_holding:
            if holding > 1:
                self.commander.issue(commands.Charge, bot, random.choice([b.position for b in bot.visibleEnemies]))
            else:
                target = self.commander.level.findRandomFreePositionInBox((bot.position-5.0, bot.position+5.0))
                self.commander.issue(commands.Attack, bot, target, lookAt = random.choice([b.position for b in bot.visibleEnemies]))

        
        
    def enter(self):        
        pass
    
    def exit(self):
        pass

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
        
    def execute(self):
        
        arrived = map(lambda x: inArea(x.position, self.position), self.bots)
        arrived = all(arrived)
        if arrived:
            self.squad.changeState(self.squad.prevState.pop())
            return
        idle = map(lambda x: x.state == BotInfo.STATE_IDLE, self.bots)
        idle = all(idle)
        if(self.priority == 0 and idle):
            for bot in self.bots:
                self.sneak(bot, self.position)
                bot.changeState(ChargePosition(bot, self.paths[bot]))
        else:
            for bot in self.bots:
                bot.update()
        
    def enter(self):        
        for bot in self.bots:
            if(self.priority == 0):
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
        self.Vectors = defDirs
        self.assignDefenders(squad.bots)
        self.numAliveDefenders = len(squad.bots)
        self.priority = priority
        self.graph = graph
        
                
    def assignDefenders(self, defenders):
        if not defenders:
            return
        if isinstance(self.Vectors, list):
            if self.Vectors:
                splitVectors = list(chunks(self.Vectors, min(len(defenders), len(self.Vectors))))
                for i, bot in enumerate(defenders):
                    bot.defending_direction = splitVectors[(i+1)%len(splitVectors)]
        else:
            for bot in defenders:
                bot.defending_direction = self.Vectors
            
    def reAssignRoles(self):
        aliveDefenders = filter(lambda x: x.health > 0, self.bots)
        self.assignDefenders(aliveDefenders)
        for bot in aliveDefenders:
            bot.defenceTrigger = 1
            
    def execute(self):
        for defender in self.bots:
            if not inArea(defender.position, self.position):
                self.squad.changeState(Attack(self.squad, self.position, self.isCorner, self.priority, self.graph))
                return
        aliveDefenders = [defender for defender in self.bots if defender.health > 0]
        if len(aliveDefenders) != self.numAliveDefenders:
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
    
    def enter(self):
        for bot in self.bots:
            bot.changeState(AttackPostition(bot, random.choice(self.positions)))
    
    def execute(self):
        for bot in self.bots:
            if (bot.state == BotInfo.STATE_IDLE):
                bot.changeState(AttackPostition(bot, random.choice(self.positions)))
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
        for bot in self.bots:
            if bot.flag:
                self.weHaveFlag = True
                self.flagBearer = bot
        if self.weHaveFlag and not any(map(lambda x: x.flag, self.bots)):
            self.weHaveFlag = False
                    
        for bot in self.bots:
            if bot.state == BotInfo.STATE_IDLE:
                if self.weHaveFlag:
                    if bot.flag:
                        self.sneak(bot, bot.commander.game.team.flagScoreLocation)
                        bot.changeState(ChargePosition(bot, self.paths[bot]))
                else:
                    self.sneak(bot, bot.commander.game.enemyTeam.flag.position)
                    bot.changeState(ChargePosition(bot, self.paths[bot]))
            else:
                bot.update()
                
    def exit(self):
        pass