from pybrain.structure import FeedForwardNetwork
from pybrain.structure import LinearLayer, SigmoidLayer
from pybrain.structure import FullConnection
from states import DefendingSomething, AttackPostition, ChargePosition
from api.vector2 import Vector2
import pickle
from api.gameinfo import BotInfo
from util import inVOF, distance

class BotBrain():
    def __init__(self, bot, commander, i):
        try:
            with open('bot' + str(i), 'r') as f:
                self.net = pickle.load(f)
        except Exception as e:
            print e
            net = FeedForwardNetwork()
            inputLayer = LinearLayer(70)
            hiddenLayer = SigmoidLayer(40)
            outLayer = SigmoidLayer(commander.level.width + commander.level.height)
            net.addInputModule(inputLayer)
            net.addModule(hiddenLayer)
            net.addOutputModule(outLayer)
            in_to_hidden = FullConnection(inputLayer, hiddenLayer)
            hidden_to_out = FullConnection(hiddenLayer, outLayer)
            net.addConnection(in_to_hidden)
            net.addConnection(hidden_to_out)
            net.sortModules()
            net.randomize()
            self.net=net
        self.bot = bot
        self.commander = commander
        self.hadFlag = False
        self.numOfFlagsGotten = 0
        self.events = set()
        
    
    def doSomething(self):
        events = self.commander.game.match.combatEvents
        events = [event for event in events if event not in self.events]
        enemies = list(self.bot.visibleEnemies)
        for enemy in self.bot.visibleEnemies:
            if inVOF(self.bot, enemy, self.commander.level.fieldOfViewAngles[self.bot.state]) and distance(self.bot.position, enemy.position) < 15:
                enemies.remove(enemy)
        if self.bot.state == BotInfo.STATE_IDLE or self.bot.state == BotInfo.STATE_HOLDING or (events and not self.bot.state == BotInfo.STATE_TAKINGORDERS and not enemies):
            self.events = self.events.union(events)
            if self.bot.flag and not self.hadFlag:
                self.hadFlag = True
                self.numOfFlagsGotten+=1
            if not self.bot.flag and self.hadFlag:
                self.hadFlag = False
            inpt = ()
            inpt += (self.bot.position.x, self.bot.position.y)
            enemyPositions = 30*[0]
            for i, enemy in enumerate(self.bot.visibleEnemies):
                enemyPositions[2*i] = enemy.position.x
                enemyPositions[2*i+1] = enemy.position.y
            inpt += tuple(enemyPositions)    
            
            teamPositions = 30*[0]
            for i, member in enumerate(self.commander.game.bots_alive):
                teamPositions[2*i] = member.position.x
                teamPositions[2*i+1] = member.position.y
            inpt += tuple(teamPositions)
            
            inpt += (self.commander.game.team.flag.position.x, self.commander.game.team.flag.position.y)
            inpt += (self.commander.game.enemyTeam.flag.position.x, self.commander.game.enemyTeam.flag.position.y)
            inpt += (self.commander.game.team.flagScoreLocation.x, self.commander.game.team.flagScoreLocation.y)
            inpt += (self.commander.game.enemyTeam.flagScoreLocation.x, self.commander.game.enemyTeam.flagScoreLocation.y)
    
            output = self.net.activate(inpt)
            output = list(output)
            x = output[:self.commander.level.width].index(max(output[:self.commander.level.width]))
            y = output[self.commander.level.width:self.commander.level.height+self.commander.level.width].index(max(output[self.commander.level.width:self.commander.level.height+self.commander.level.width]))
            position = self.commander.level.findNearestFreePosition(Vector2(x, y))
            self.bot.changeState(AttackPostition(self.bot, position))
        else:
            self.bot.update()
        
        
        

        