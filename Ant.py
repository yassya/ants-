from ants import *
from collections import deque
from numpy import array
from MyBot import MyBot
from MyBot import isDebug
from heapq import *

class Ant:
	loc = (-1, -1)
	velo = array([0, 0])
	orderName = ""
	waypoints = deque()
	def __init__(self, pLoc):
		self.target = (-1, -1)
		self.loc = pLoc
		self.usedForFoodRecalc = False
		self.isAttacking = False
		self.isExploring=False
	def __eq__(self, other):  #ah well :)
		return self.loc == other
	def __repr__(self):
		return repr((self.loc, self.target))
	def cancelOrder(self):
		self.orderName = ''
		self.target = (-1, -1)
		self.waypoints = deque()
	def debugPrint(self, msg):
			if isDebug:
				f = open('debug.txt', 'a')
				f.write(str(msg) + "\n")
				f.close()
	def hasTarget(self):
		if self.orderName == '5':
			return True
		if self.orderName == '4':
			return False
		return self.target != (-1, -1)
	def getTarget(self):
		return self.target
	def generateWaypoints(self, target, bot, ants):
		wp = deque()
		loc_temp = self.loc
		while loc_temp != target:
			next_wp = random.choice(ants.direction(loc_temp, target))
			wp.append(next_wp)
			loc_temp = ants.destination(loc_temp, next_wp)
		return wp
	
	# wikipedia-algorithm implementation for A*
	def generateWaypointsAStar(self, target, bot, ants):
		if self.loc == target:
			return deque()
		def reconstruct_path(node):
			directions = deque()
			directions.appendleft( ants.direction(came_from[node], node)[0] )
			node = came_from[node]
			while node != self.loc:
				directions.appendleft( ants.direction(came_from[node], node)[0] )
				node = came_from[node]
			return directions
		
		closedset = set()
		openset = set()
		openset.add(self.loc)
		fHeap = []
		came_from = {}
		g_score = {self.loc:0}
		heappush( fHeap, (g_score[self.loc] + ants.distance(self.loc, target)*3, self.loc) )
		
		while openset:
			x = heappop( fHeap )[1]
			while x not in openset:
				x = heappop( fHeap )[1]
			
			if x == target:
				return reconstruct_path(target)
			openset.remove(x)
			closedset.add(x)
			
			for y in bot.mapNeighbours[x]:
				if y in closedset:
					continue
				tentative_g_score = g_score[x] + ants.distance(x, y)
				
				tentative_is_better = False
				if y not in openset:
					openset.add(y)
					tentative_is_better = True
				elif tentative_g_score < g_score[y]:
					tentative_is_better = True
				
				if tentative_is_better:
					came_from[y] = x
					g_score[y] = tentative_g_score
					heappush( fHeap, (tentative_g_score + ants.distance(y, target)*3, y) )

	def tryOrder(self, ptarget, ants, ordername, bot):
		if bot.rememberedMap[ptarget[0]][ptarget[1]] != 3 and bot.rememberedMap[ptarget[0]][ptarget[1]] != 4 and ptarget != self.target:
			self.target = ptarget
			self.debugPrint("order " + str(ordername) + ": " + str(self.loc) + " -> " + str(ptarget))
			self.waypoints = self.generateWaypointsAStar(ptarget, bot, ants)
			self.orderName = ordername
			bot.debugOrderCounter[ordername] += 1
			if ordername!='6' and self.isExploring:
				self.isExploring=False
	def move(self, ants, bot):
		if self.orderName == '6':
			self.debugPrint(self.waypoints)
			self.debugPrint(self.loc)
			self.debugPrint(self.target)
			self.debugPrint(bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]),ants))
		if self.waypoints and bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			
			if self.orderName == '5' and ants.destination(self.loc, self.waypoints[0]) == self.target:
				next_wp = self.waypoints[0]
				ants.issue_order((self.loc, next_wp))
				self.velo = (0, 0)
				self.loc = ants.destination(self.loc, next_wp)
				self.waypoints.popleft()
				bot.soonOccupied.add(self.loc)
			elif self.orderName == '5' and (ants.destination(self.loc, self.waypoints[0]) in ants.my_ants() or ants.destination(self.loc, self.waypoints[0]) in bot.soonOccupied):
				self.velo = (0, 0)
		
				pass #thats right, in that case we *want* to wait until the field is free!
			else:
				self.debugPrint(self.orderName)
				self.waypoints = self.generateWaypointsAStar(self.target, bot, ants)
		elif self.waypoints and not bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			next_wp = self.waypoints[0]
			#run away from enemy ants
			ownAnts=set()
			nEnemyAnts = 0
			for enAnt in ants.enemy_ants():
				if ants.radius2(enAnt[0], ants.destination(self.loc, next_wp)) <= ants.attackradius2+1:
					nEnemyAnts += 1
					ownAnts|=bot.closebyEnemyAntsDistances[enAnt[0]]
#			self.debugPrint(ownAnts)
			if nEnemyAnts>0 and nEnemyAnts >= len(ownAnts):
				if not bot.isBlockedLoc(ants.destination(self.loc, bot.oppositeDirection(next_wp)), ants):
					self.waypoints.appendleft(next_wp)
					self.waypoints.appendleft(next_wp)#go back next turn
					next_wp = bot.oppositeDirection(next_wp)#these 3 lines can be replaced by more sophisticated flee direction
					self.waypoints.appendleft(next_wp)#the right element needs to be popped
			desti = ants.destination(self.loc, next_wp)
			ants.issue_order((self.loc, next_wp))
			self.velo = (desti[0] - self.loc[0], desti[1] - self.loc[1])
			self.loc = desti
			self.waypoints.popleft()
			bot.soonOccupied.add(self.loc)
		if not self.waypoints:
			self.velo = (0, 0)
			if not self.orderName == '5':
				self.cancelOrder()
				
				
	def boidMove(self, bot,ants, nAnts):
		perc_center = bot.AntCenter - self.loc
		perc_center = perc_center / (nAnts - 1)
		center_bias = (perc_center - self.loc)/8

		perc_velo = bot.AntVelo - self.velo
		perc_velo = perc_velo / (nAnts - 1)
		velo_bias = (perc_velo - self.velo)/1
		
		minHill=array([-1,-1])
		minDist=9999
		for hill in ants.my_hills():
			dist=ants.distance(self.loc,hill)
			if dist<minDist:
				minDist=dist
				minHill=array(hill)
		hill_bias=minHill-self.loc
		hill_bias=hill_bias/(minDist+1)
		
		chill=array([0,0])
		nAnts=0
		for otherAnt in [a for a in bot.antList if a.loc !=self.loc and a.orderName!='5']:
			if ants.distance(otherAnt.loc,self.loc)<10:
				chill=chill+self.loc
				chill=chill-otherAnt.loc
				nAnts+=1
		
		
		deltaV=self.velo+center_bias+velo_bias+chill+hill_bias
		
		dX=round(deltaV[0])
		dY=round(deltaV[1])
		deltaV=array([dX,dY])
		
		
		
		
#		
#		self.debugPrint("Ant at \t"+str(self.loc))
#		self.debugPrint("\tPerc. center\t"+str(perc_center))
#		self.debugPrint("\tCenter Bias\t"+str(center_bias))
#		self.debugPrint("\tPerc. velo\t"+str(perc_velo))
#		self.debugPrint("\tVelo bias\t"+str(velo_bias))
#		self.debugPrint("\tChill\t\t"+str(chill))
#		self.debugPrint("\tPerc. Hill\t"+str(minHill))
#		self.debugPrint("\tHill Distance\t"+str(minDist))
#		self.debugPrint("\tHill Bias\t"+str(hill_bias))
#		self.debugPrint("\tdeltaV\t\t"+str(deltaV))
		target=(int(self.loc[0]+dX)%ants.rows,int(self.loc[1]+dY)%ants.cols)
#		self.debugPrint("\tnew target\t"+str(target))
		self.tryOrder(target, ants, '4', bot)