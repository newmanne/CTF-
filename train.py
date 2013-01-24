from pybrain.structure import FeedForwardNetwork
from pybrain.structure import LinearLayer, SigmoidLayer
from pybrain.structure import FullConnection
from pybrain.datasets import SupervisedDataSet
from pybrain.supervised.trainers import BackpropTrainer
import ast
import pickle
import numpy
import neat

from numpy import linalg

def train():
    net = FeedForwardNetwork()
    inputLayer = LinearLayer(88*50 + 4)
    hiddenLayer = SigmoidLayer(66)
    outLayer = LinearLayer(1)
    net.addInputModule(inputLayer)
    net.addModule(hiddenLayer)
    net.addOutputModule(outLayer)
    in_to_hidden = FullConnection(inputLayer, hiddenLayer)
    hidden_to_out = FullConnection(hiddenLayer, outLayer)
    net.addConnection(in_to_hidden)
    net.addConnection(hidden_to_out)
    net.sortModules()
    dataset = SupervisedDataSet(88*50 + 4, 1)
    List = open("data.txt").readlines()
#    print "Collecting Data"
#
#    singleData = ast.literal_eval(List[0])
#    print len(List), len(singleData[0])
#    x = numpy.zeros((len(List), len(singleData[0])))
#    for i, line in enumerate(List):
#        singleData = ast.literal_eval(line)
#        for k, j in enumerate(singleData[0]):
#            x[i,k] = j
#    print x
#    print x.shape
#    m = x.shape[0]
#    sigma = 0
#    for i in range(m):
#        sigma += numpy.dot(numpy.transpose(numpy.asmatrix(x[i])), numpy.asmatrix(x[i]))
#    sigma = sigma/m
#    print sigma.shape
#    u, s, v = linalg.svd(sigma)
#    print u.shape
#    sumTemp = 0
#    totalSum = numpy.diag(s).sum()
#    finalK = 0
#    for k in range(u.shape[0]):
#        sumTemp += s[k]
#        if sumTemp/totalSum > 0.99:
#            finalK = k
#    if finalK == 0:
#        k = u.shape[0]
#    Ureduce = u[:, 0:k]
#    z = numpy.zeros((len(List), k))
#    for i in range(m):
#        print numpy.transpose(Ureduce).shape, numpy.asmatrix(x[i]).shape
#        temp = numpy.dot(numpy.transpose(Ureduce), numpy.transpose(numpy.asmatrix(x[i])))
#        for k, j in enumerate(temp):
#            z[i, k] = j
#    
#    net = FeedForwardNetwork()
#    inputLayer = LinearLayer(len(z[0]))
#    hiddenLayer = SigmoidLayer(66)
#    outLayer = LinearLayer(1)
#    net.addInputModule(inputLayer)
#    net.addModule(hiddenLayer)
#    net.addOutputModule(outLayer)
#    in_to_hidden = FullConnection(inputLayer, hiddenLayer)
#    hidden_to_out = FullConnection(hiddenLayer, outLayer)
#    net.addConnection(in_to_hidden)
#    net.addConnection(hidden_to_out)
#    net.sortModules()
#    dataset = SupervisedDataSet(len(z[0]), 1)
    print "Collecting Output Data"
    for i, line in enumerate(List):
        singleData = ast.literal_eval(line)
        dataset.addSample(singleData[0], singleData[1])
        
    print "done collecting, now training"
    trainer = BackpropTrainer(net, verbose=True,momentum=0.018, learningrate=0.005)
    trainer.trainUntilConvergence(dataset, maxEpochs=500)
    
    fileObject = open('network', 'w')
    pickle.dump(net, fileObject)
if __name__ == '__main__':
    train()