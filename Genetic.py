from api.commander import Commander

from bot import Bot
from botbrain import BotBrain
import pickle
from graph import setupGraphs
import numpy
import random

class GeneticCommander(Commander):
    """
    Sends everyone to randomized positions or a random choice of flag location.  The behavior of returning the flag
    to the home base after capturing it is purely emergent!
    """
    events = set()

    def tick(self):
        """Process all the bots that are done with their orders and available for taking commands."""
        # The 'bots_available' list is a dynamically calculated list of bots that are done with their commands.
        for brain in self.botBrains:
            brain.doSomething()
                
    def initialize(self):
        setupGraphs(self)
        self.verbose = False
        self.botBrains = []
        for i, bot_info in enumerate(self.game.bots_available):
            bot = Bot(bot_info, self)
            botBrain = BotBrain(bot, self, i)
            self.botBrains.append(botBrain)
            
    def randomCrossover(self, brainOne, brainTwo):
        netOne = brainOne.net.params
        netTwo = brainTwo.net.params
        if random.random() < 0.7:
            crossoverAt = random.randint(0, len(brainTwo.net.params)-1)
            netTotal = netOne[:crossoverAt]
            netTotal = numpy.append(netTotal,netTwo[crossoverAt:])
            brainOne.net._setParameters(netTotal)
            if random.random() < 0.01:
                brainOne.net.mutate()
            
    def rouletteSelectBrain(self):
        totalScore = reduce(lambda x, y: x+y, map(lambda x:x.bot.score, self.botBrains))
        fSlice = random.random()*totalScore
        currScore = 0
        for i in range(len(self.botBrains)):
            currScore += self.botBrains[i].bot.score
            if currScore > fSlice:
                return self.botBrains[i]
        return random.choice(self.botBrains)
            
    def crossoverBrains(self):
        for brain in self.botBrains:
            print brain.bot.score
        for _ in range(len(self.botBrains)):
            self.randomCrossover(self.rouletteSelectBrain(), self.rouletteSelectBrain())
            
    def shutdown(self):
        self.crossoverBrains()
        for i, brain in enumerate(self.botBrains):
            with open('bot' + str(i), 'w') as f:
                pickle.dump(brain.net, f)

