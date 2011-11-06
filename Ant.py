from ants import *
from collections import deque
from MyBot import MyBot
from MyBot import isDebug

class Ant:
	loc = (-1, -1)
	
	orderName = ""
	waypoints = deque()
	def __init__(self, pLoc):
		self.target = (-1, -1)
		self.loc = pLoc
		self.usedForFoodRecalc = False
		self.isAttacking=False
#		self.doNotMove=False
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
		if self.orderName=='5':
			return True
		if self.orderName=='4':
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
		
	# A* with JPS
	def generateWaypointsJPS(self, target, bot, ants):
		if self.loc == target:
			return deque()
		def getNNodes(loc):
			l = []
			l.append(ants.destination(loc, 'n'))
			l.append(ants.destination(loc, 'e'))
			l.append(ants.destination(loc, 's'))
			l.append(ants.destination(loc, 'w'))
			return l
			
		def jump(c,n,s,g):
			direct=ants.direction(c, n) # n contains field, dir n,e,s,w
			if bot.rememberedMap[direct[0]][direct[1]]== 3:
				return 0
			if n==g:
				return n
		def prune(s,x,y):
			return ants.distance(s,y)>=ants.distance(x,y)
			
			
		def reconstruct_path(successors):
			pass

		currNode=self.loc
		startNode=self.loc
		goalNode=target
		
		successors=deque()
		for y in [n for n in getNNodes(currNode) if not prune(startNode,currNode,n)]:
			jumpPoints=jump(currNode,n,startNode,goalNode)
			successors=(jumpPoints)
		return reconstruct_path(successors)
	
	# wikipedia-algorithm implementation for A*
	def generateWaypointsAStar(self, target, bot, ants):
		if self.loc == target:
			return deque()
		breakingFactor = (1+1.0/ants.distance(self.loc,target))
		def heuristic_cost_estimate(loc1, loc2):
			return ants.distance(loc1, loc2)*breakingFactor
		def reconstruct_path(node):
			path = deque()
			path.appendleft(ants.direction(came_from[node], node)[0])
			node = came_from[node]
			while node != self.loc:
				path.appendleft(ants.direction(came_from[node], node)[0])
				node = came_from[node]
			return path
		
		closedset = set()
		openset = set()
		openset.add(self.loc)
		came_from = {}
		
		g_score = {self.loc:0}
		h_score = {self.loc:heuristic_cost_estimate(self.loc, target)}
		f_score = { self.loc : g_score[self.loc] + h_score[self.loc] }
		
		whilecounter = 0
		while openset:
			whilecounter += 1
			x = min(f_score, key=f_score.get)
			
			if x == target:
				return reconstruct_path(target)
			openset.remove(x)
			del f_score[x]
			
			closedset.add(x)

			for y in [n for n in bot.mapNeighbours[x]]:
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
					h_score[y] = heuristic_cost_estimate(y, target)
					f_score[y] = g_score[y] + h_score[y]

	def tryOrder(self, ptarget, ants, ordername, bot):
		if bot.rememberedMap[ptarget[0]][ptarget[1]] != 3 and bot.rememberedMap[ptarget[0]][ptarget[1]] != 4 and ptarget != self.target:
			self.target = ptarget
			self.debugPrint("order " + str(ordername) + ": " + str(self.loc) + " -> " + str(ptarget))
			self.waypoints = self.generateWaypointsAStar(ptarget, bot, ants)
			self.orderName = ordername
			bot.debugOrderCounter[ordername] += 1
	def move(self, ants, bot):
		if self.orderName=='5':
			self.debugPrint(self.waypoints)
		if self.waypoints and bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			if self.orderName=='5' and ants.destination(self.loc, self.waypoints[0])==self.target:
				next_wp = self.waypoints[0]
				ants.issue_order((self.loc, next_wp))
				self.loc = ants.destination(self.loc, next_wp)
				self.waypoints.popleft()
				bot.soonOccupied.add(self.loc)
			elif self.orderName=='5' and ants.destination(self.loc, self.waypoints[0]) in ants.my_ants():
				pass #thats right, in that case we *want* to wait until the field is free!
			else:
				self.waypoints = self.generateWaypointsAStar(self.target, bot, ants)
		elif self.waypoints and not bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			next_wp = self.waypoints[0]
			#run away from enemy ants
			nCloseAnts=0
			for myAnt in [j for j in ants.my_ants() if ants.distance(j, self.loc)<=3]:
				nCloseAnts+=1
			nEnemyAnts=0
			for enAnt in ants.enemy_ants():
				if ants.distance(enAnt[0], ants.destination(self.loc,next_wp))<=3:
					nEnemyAnts+=1
			if nEnemyAnts>=nCloseAnts:
				if not bot.isBlockedLoc(ants.destination(self.loc, bot.oppositeDirection(next_wp)), ants):
					self.waypoints.appendleft(next_wp)
					self.waypoints.appendleft(next_wp)#go back next turn
					next_wp=bot.oppositeDirection(next_wp)#these 3 lines can be replaced by more sophisticated flee direction
					self.waypoints.appendleft(next_wp)#the right element needs to be popped
					
			ants.issue_order((self.loc, next_wp))
			self.loc = ants.destination(self.loc, next_wp)
			self.waypoints.popleft()
			bot.soonOccupied.add(self.loc)
		if not self.waypoints:
			if not self.orderName=='5':
				self.cancelOrder()
			