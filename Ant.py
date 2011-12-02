from ants import *
from collections import deque
from MyBot import MyBot
from MyBot import isDebug
from heapq import *
from copy import *

class Order:
	def __init__(self, pDistance, pPoints, pTarget, pOrdername, pPath):
		self.value = 1.0*pPoints/pDistance
		self.distance = pDistance
		self.points = pPoints
		self.target = pTarget
		self.targetBorder = None
		self.ordername = pOrdername
		self.path = pPath

	def __repr__(self):
		return repr(( self.value, self.distance, self.points, self.target, self.ordername, self.path, self.targetBorder ))
	def __lt__(self, other): #for sorting
		return self.value < other.value

class Ant:					
	def __init__(self, pLoc):
		self.loc = pLoc
		self.orders = []
		self.activeOrder = None
	def __eq__(self, other):  #ah well :)
		return self.loc == other
	def __repr__(self):
		return repr((self.loc))
	def cancelOrder(self):
		self.target = (-1, -1)
	def debugPrint(self, msg):
			if isDebug:
				f = open('debug.txt', 'a')
				f.write(str(msg) + "\n")
				f.close()
	
	def evalOrders(self):
		if self.orders:
			self.orders.sort( reverse=True )
			# for o in self.orders:
				# self.debugPrint("self.orders: "+str( o ))
	
	def move(self, ants, bot):
		if self.orders:			
			orderDir = ants.direction(self.loc, self.activeOrder.path[0])[0]
			orderDest = self.activeOrder.path[0]
			if not bot.isBlockedLoc( orderDest, ants ) and not orderDest in ants.food():
				# self.debugPrint("order " + str(self.orders[0]))
				ants.issue_order((self.loc, orderDir))
				bot.soonOccupied.add( orderDest )
				self.activeOrder.path.popleft()
				
				bot.antList[orderDest] = bot.antList[self.loc]
				del bot.antList[self.loc]
				self.loc = orderDest
	