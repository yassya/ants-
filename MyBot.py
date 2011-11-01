#!/usr/bin/env python
from ants import *
import sys
from operator import itemgetter, attrgetter
from collections import deque
import Ant

isDebug = False # Debug Flag to toggle Debug Output into "debug.txt". Has to been False for submitting!

class Ant:
	loc = (-1, -1)
	
	orderName = ""
	waypoints = deque()
	def __init__(self, pLoc):
		self.target = (-1, -1)
		self.loc = pLoc
		self.usedForFoodRecalc = False
	def __eq__(self, other):  #ah well :)
		return self.loc == other
	def __repr__(self):
		return repr((self.loc, self.target))
	def debugPrint(self, msg):
			if isDebug:
				f = open('debug.txt', 'a')
				f.write(str(msg) + "\n")
				f.close()
	def hasTarget(self):
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
		if bot.rememberedMap[ptarget[0]][ptarget[1]] != 3 and ptarget != self.target:
			self.target = ptarget
			self.debugPrint("order " + str(ordername) + ": " + str(self.loc) + " -> " + str(ptarget))
			self.waypoints = self.generateWaypointsAStar(ptarget, bot, ants)
			self.orderName = ordername
			bot.debugOrderCounter[ordername] += 1
	def move(self, ants, bot):
		if self.waypoints and bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			self.waypoints = self.generateWaypointsAStar(self.target, bot, ants)
		if self.waypoints and not bot.isBlockedLoc(ants.destination(self.loc, self.waypoints[0]), ants):
			next_wp = self.waypoints[0]
			#run away from enemy ants:
			for enAnt in ants.enemy_ants():
				if ants.distance(enAnt[0], ants.destination(self.loc,next_wp))<=3:
					if not bot.isBlockedLoc(ants.destination(self.loc, bot.oppositeDirection(next_wp)), ants):
						self.waypoints.appendleft(next_wp)
						self.waypoints.appendleft(next_wp)#go back next turn
						next_wp=bot.oppositeDirection(next_wp)#these 3 lines can be replaced by more sophisticated flee direction
						self.waypoints.appendleft(next_wp)#the right element needs to be popped
						break
			ants.issue_order((self.loc, next_wp))
			self.loc = ants.destination(self.loc, next_wp)
			self.waypoints.popleft()
			bot.soonOccupied.add(self.loc)
		else:
			 self.target = (-1, -1)
		
class Food:
	def __init__(self, pLoc):
		self.loc = (-1, -1)
		self.comingAnt = None
		self.loc = pLoc
		self.usedForFoodRecalc = False
	def hasComingAnt(self):
		return self.comingAnt != None
	def debugPrint(self, msg):
		if isDebug:
			f = open('debug.txt', 'a')
			f.write(str(msg) + "\n")
			f.close()
		
class MyBot:
	knownMap = [] #first simple definition: 0=unknown, >=1 known since turn n
	
	# all known information usable for pathfinding and attacking/food orders!
	# -1: still unknown
	# 0: free or own ant
	# 1: food
	# 2: enemy hill
	# 3: wall/water
	rememberedMap = []
	
	def __init__(self):
		self.turnnumber = 0
		self.mapAspect = 4.2
		self.enemyHills = [] # remembered locations of detected enemy hills
		self.foods = {}
		self.soonOccupied = set() # keep track of what locations will be occupied by ants next round
		self.antList = []
		self.debugOrderCounter = {'1':0, '2':0, '3':0, '4':0} # keep track how orders are distributed
		if isDebug:
			f = open('debug.txt', 'w')
			f.close()
		self.maxCPULoad = [-1,-1] # (round, runtime),
		self.mapNeighbours = {} # keeps a list of adjacent map locations to speed up A*

	def do_setup(self, ants):
		self.mapAspect = 1.0 * ants.cols / ants.rows
		self.knownMap = [[0 for col in range(ants.cols)]
			for row in range(ants.rows)]
		self.rememberedMap = [[-1 for col in range(ants.cols)]
			for row in range(ants.rows)]
		
		for row in range(0, ants.rows):
			for col in range(0, ants.cols):
				loc = row, col
				l = []
				l.append(ants.destination(loc, 'n'))
				l.append(ants.destination(loc, 'e'))
				l.append(ants.destination(loc, 's'))
				l.append(ants.destination(loc, 'w'))
				self.mapNeighbours[loc] = l
				
	# follow gradient of unknown map squares
	def gradientTarget(self, loc, ants):
		row, col = loc
		scanRange = 5
		maxNew = 0
		bestPos = []
		
		#find field(s) with the highest value
		for rowPos in range(row - scanRange, row + scanRange + 1):
			for colPos in range(col - scanRange, col + scanRange + 1):
				rowPos = (rowPos + ants.rows) % ants.rows
				colPos = (colPos + ants.cols) % ants.cols
				currVal = self.knownMap[rowPos % ants.rows][colPos % ants.cols]
				if currVal > maxNew and loc != (rowPos % ants.rows, colPos % ants.cols) and self.rememberedMap[rowPos % ants.rows][colPos % ants.cols] != 3:
					maxNew = currVal
					bestPos = [ (rowPos % ants.rows, colPos % ants.cols)]
					
				elif currVal == maxNew and currVal != 0 and loc != (rowPos % ants.rows, colPos % ants.cols):					
					bestPos.append((rowPos % ants.rows, colPos % ants.cols))
		return bestPos
	
	def debugPrint(self, msg):
		if isDebug:
			f = open('debug.txt', 'a')
			f.write(str(msg) + "\n")
			f.close()
	
	# random direction, but adjusted for map aspect
	def randDirection(self):
		aspectNumber = random.uniform(0, 1.0 + self.mapAspect)
		if aspectNumber > 1.0:
			return random.choice(['w', 'e'])
		else:
			return random.choice(['n', 's'])
	
	# if random number is 0,1,2,3: random Direction. If higher: go to 'biasedDirection'
	def randDirectionBiased(self, biasedDirection):
		number = random.randrange(0, 6)
		if number <= 3:
			return self.randDirection()
		else:
			return biasedDirection
	
	def oppositeDirection(self, dir):
		return {'n':'s', 'e':'w', 's':'n', 'w':'e'}[dir]
	
# return true if loc is blocked by wall or ant (of that ant doesn't move away) or will be blocked by ant next turn
	def isBlockedLoc(self, loc, ants):
		if not ants.passable(loc): # water
			return True
		elif loc in self.soonOccupied: # ant next round
			return True
		elif not ants.unoccupied(loc): # ant
			
			#fill list of used ants by hand
			# usedAnts= [a for a in self.antList if a.hasTarget()]
			# if loc in usedAnts and loc not in self.soonOccupied:
				# return False
			# elif loc in usedAnts and loc in self.soonOccupied:
				# return True
			# elif loc not in usedAnts:
				# return True
			return True
		else:
			return False

	# inserts ins into list while keeping ascending order
	def sortedInsert(self,list,ins):
		if not list:
			list.append(ins)
			return list
		else:
			for i in range(len(list)):
				if ins[1]<list[i][1]:
					list.insert(i,ins)
					return list
			list.append(ins)
			return list

	def do_turn(self, ants):
		self.turnnumber += 1
		self.debugPrint("\nTURN " + str(self.turnnumber))
		# keep track how orders are distributed
		self.debugOrderCounter['1'] = 0
		self.debugOrderCounter['2'] = 0
		self.debugOrderCounter['3'] = 0
		self.debugOrderCounter['4'] = 0
		
		# if self.turnnumber in [1,14,61]:
			# self.debugPrint("wall: "+str(self.rememberedMap[9][65]))
		
		time1=time.clock()
		
		# clear the housekeeping sets
		self.soonOccupied.clear()
		
		# check if saved enemy hills are still there
		for hill in [a for a in self.enemyHills if ants.visible(a[0]) and a not in ants.enemy_hills()]:
			self.enemyHills.remove(hill)
			# ants attacking that hill are now free again
			for ant in [a for a in self.antList if a.getTarget() == hill[0] and a.orderName == '2']:
				ant.orderName = ''
				ant.target = (-1, -1)

		# update list of enemy hills if new ones become visible
		for hill in [a for a in ants.enemy_hills() if a not in self.enemyHills]: 
			self.enemyHills.append(hill)

		# remove eaten food
		for eatenFoodLoc in [a for a in self.foods if ants.visible(a) and a not in ants.food()]:
			# check in case food got eaten by enemy ant or accidentally
			if self.foods[eatenFoodLoc].hasComingAnt() and self.foods[eatenFoodLoc].comingAnt.orderName=="1":
				self.foods[eatenFoodLoc].comingAnt.orderName = ''
				self.foods[eatenFoodLoc].comingAnt.target = (-1, -1)
			# clear distances
			for otherFoodLoc in [a for a in self.foods if a != eatenFoodLoc]: 
				deletingDist = ants.distance(eatenFoodLoc, otherFoodLoc)
				self.foods[otherFoodLoc].foods.remove( (eatenFoodLoc, deletingDist ) )
			del self.foods[eatenFoodLoc]
		
		# new food visible
		for newFoodLoc in [a for a in ants.food() if a not in self.foods]:
			self.foods[newFoodLoc] = Food(newFoodLoc)
			
			#add distances to other known foods
			for otherFoodLoc in [a for a in self.foods if a != newFoodLoc]: 
				dist = ants.distance(newFoodLoc, otherFoodLoc)
				self.sortedInsert( self.foods[newFoodLoc].foods, (otherFoodLoc,dist) )
				self.sortedInsert(self.foods[otherFoodLoc].foods, (newFoodLoc,dist))

		#update the map
		for row in range(0, ants.rows):
			for col in range(0, ants.cols):
				loc = row, col
				if ants.visible(loc):
					if not ants.passable(loc):
						if self.rememberedMap[row][col] != 3:
							for neigh in self.mapNeighbours[loc]:
								self.mapNeighbours[neigh].remove(loc)
							self.rememberedMap[row][col] = 3
					if self.knownMap[row][col] == 0:
						self.knownMap[row][col] = self.turnnumber			
		
		#add newborn ants to antlist				
		for locAntNewborn in [a for a in ants.my_hills() if not a in self.antList]:
				if not ants.unoccupied(locAntNewborn):
					newAnt = Ant(locAntNewborn)
					self.debugPrint("newAnt: " + str(newAnt))
					self.antList.append(newAnt)
		
		# remove killed ants ;(
		aliveAntsLoc = set(ants.my_ants())
		for ant in [a for a in self.antList if a.loc not in aliveAntsLoc]:
			self.debugPrint("killedAnt: " + str(ant))
			self.antList.remove(ant)
		
		time2=time.clock()
		
		# priority 1: Gather every food item by closest ant
		foodDistances = []	
		for foodLoc in [f for f in self.foods]:
			for ant in [a for a in self.antList]:
				self.foods[foodLoc].usedForFoodRecalc = False
				ant.usedForFoodRecalc = False
				dist_temp = ants.distance(foodLoc, ant.loc)
				foodDistances.append((dist_temp, ant, foodLoc))
		foodDistances.sort(key=itemgetter(0))
		
		for dist in foodDistances:
			activeFood = self.foods[dist[2]]
			activeAnt = dist[1]
			
			# closest food calculation
			isSkipBecauseTime = False
			if len(self.foods)>1 and len(self.antList)>1:
				foodNeigh = self.foods[ activeFood.foods[0][0] ]
				isFoodNeighTargeted = foodNeigh.hasComingAnt()
				if isFoodNeighTargeted:
					distA2F2 = ants.distance(activeAnt.loc, dist[2]) #from potential ant to potential food
					distA1F1 = ants.distance(foodNeigh.loc, foodNeigh.comingAnt.loc) #from food Neighbour to its coming ant
					distF1F2 = ants.distance(dist[2], foodNeigh.loc) #from potential food to neighbour food
					if distA2F2>=(distA1F1+distF1F2):
						isSkipBecauseTime = True
			
			# hasn't been used + order hasn't already been given
			if not activeFood.usedForFoodRecalc and not activeAnt.usedForFoodRecalc and activeFood.comingAnt!=activeAnt and not isSkipBecauseTime:
				# food already had an incoming ant
				if activeFood.hasComingAnt() and activeFood.comingAnt.orderName=="1":
					activeFood.comingAnt.target = (-1,-1)
					activeFood.comingAnt = None
				
				# ant was already targeting food
				if activeAnt.hasTarget() and activeAnt.orderName=="1":
					target_of_ant = activeAnt.target
					targets_coming_ant = self.foods[target_of_ant].comingAnt
					targets_coming_ant.target = (-1,-1)
					self.foods[target_of_ant].comingAnt = None
					
				activeAnt.tryOrder(dist[2], ants, '1', self)
				activeFood.comingAnt = activeAnt
				activeFood.usedForFoodRecalc = True
				activeAnt.usedForFoodRecalc = True
			# order has already been given -> mark as used
			elif activeFood.comingAnt==activeAnt:
				activeAnt.usedForFoodRecalc = True
				activeFood.usedForFoodRecalc = True
		time3=time.clock()
		
		# priority 2: attack enemy hills. 20% of closest ants are sent to attack
		for hill in self.enemyHills:
			attackDistances = []
			for ant in [a for a in self.antList if not a.hasTarget()]:
				dist_temp = ants.distance(hill[0], ant.loc)
				attackDistances.append((dist_temp, ant, hill[0]))
			attackDistances.sort(key=itemgetter(0, 2))
			numberOfAttackAnts = int(round(0.2 * len(ants.my_ants())))
			for i in [j for j in range(numberOfAttackAnts) if len(attackDistances) >= (j + 1)]: # 20%
				attackDistances[i][1].tryOrder(attackDistances[i][2], ants, '2', self)
			
		# Temporarily commented
		"""
		# priority 2.5 defend own hills
		for hill in ants.my_hills():
			defendDistances = []
			for ant in [a for a in self.antList if not a.hasTarget()]:
				dist_temp = ants.distance(hill, ant.loc)
				defendDistances.append((dist_temp, ant, hill))
			defendDistances.sort(key=itemgetter(0, 2))
			
			numberOfDefendingAnts = int(round(0.1 * len(ants.my_ants())))
			for i in [j for j in range(numberOfDefendingAnts) if len(defendDistances) >= (j + 1)]: # 10%
				if defendDistances[i][0] > 7:
					targetLoc = (
								int(round((defendDistances[i][2][0] + ((defendDistances[i][1].loc[0] - defendDistances[i][2][0]) / 4))))%ants.rows,
								int(round((defendDistances[i][2][1] + ((defendDistances[i][1].loc[1] - defendDistances[i][2][1]) / 4))))%ants.cols
								)
					defendDistances[i][1].tryOrder(targetLoc, ants, '3', self)
				if defendDistances[i][0] <= 2:
					targetLoc = (
								int(round((defendDistances[i][2][0] - ((defendDistances[i][1].loc[0] - defendDistances[i][2][0]) ))))%ants.rows,
								int(round((defendDistances[i][2][1] - ((defendDistances[i][1].loc[1] - defendDistances[i][2][1]) ))))%ants.cols
								)
					defendDistances[i][1].tryOrder(targetLoc, ants, '3', self)
		"""
		
		time4=time.clock()
		
		# priority 3: Freshly created ants. Move away from hill into random direction
		for hill in [a for a in ants.my_hills() if a in ants.my_ants()]:
			for ant in [a for a in self.antList if a.loc == hill if not a.hasTarget()]:
				if not ants.unoccupied(ant.loc):
					adjacentPositions = []
					if not self.isBlockedLoc(ants.destination(ant.loc, 'n'), ants):
						adjacentPositions.append(ants.destination(ant.loc, 'n'))
					if not self.isBlockedLoc(ants.destination(ant.loc, 'e'), ants):
						adjacentPositions.append(ants.destination(ant.loc, 'e'))
					if not self.isBlockedLoc(ants.destination(ant.loc, 's'), ants):
						adjacentPositions.append(ants.destination(ant.loc, 's'))
					if not self.isBlockedLoc(ants.destination(ant.loc, 'w'), ants):
						adjacentPositions.append(ants.destination(ant.loc, 'w'))
				
					if adjacentPositions:
						targetNew = random.choice(adjacentPositions)
						if not self.isBlockedLoc(targetNew, ants):
							ant.tryOrder(targetNew, ants, '3', self)
						
					break
		
		time5=time.clock()
		
		# priority 4: Free ants move away from starting hill or move randomly if all own hills were killed
		# TODO: Map's with multiple hills per player
		for ant in [a for a in self.antList if not a.hasTarget()]:
			targetList = self.gradientTarget(ant.loc, ants)	
			targetNew = None
			if len(targetList) == 1:
				targetNew = targetList[0]
			else: #take a random one which points away from the anthill
				if ants.my_hills():
					hillTarget = ant.loc, ants.my_hills()[0]
					#if ants.distance(ant.loc, ants.my_hills()[0]) < 7:
					for target in [a for a in targetList if a == hillTarget]:
						targetList.remove(target)
				targetNew = random.choice(targetList)
			if targetNew != None:
				ant.tryOrder(targetNew, ants, "4", self)
		self.debugPrint("after4")
		
		time6=time.clock()

		for ant in [a for a in self.antList if a.hasTarget()]:
			ant.move(ants, self)
		
		time7=time.clock()
		
		self.debugPrint("time used: " + str(int(1000 * (time.clock() - ants.turn_start_time))) + "ms")
		if int(1000 * (time.clock() - ants.turn_start_time)) > self.maxCPULoad[1]:
			self.maxCPULoad[1] = 1000 * (time.clock() - ants.turn_start_time)
			self.maxCPULoad[0] = self.turnnumber
			self.debugPrint("new maxCPULoad: "+str(self.maxCPULoad))
			
			self.debugPrint("time update: "+str(1000 * (time2 - time1)))
			self.debugPrint("time p1: "+str(1000 * (time3 - time2)))
			self.debugPrint("time p2: "+str(1000 * (time4 - time3)))
			self.debugPrint("time p3: "+str(1000 * (time5 - time4)))
			self.debugPrint("time p4: "+str(1000 * (time6 - time5)))
			self.debugPrint("time rest: "+str(1000 * (time7 - time6)))
			
if __name__ == '__main__':
	try:
		import psyco
		psyco.full()
	except ImportError:
		pass
	try:
		Ants.run(MyBot())
	except KeyboardInterrupt:
		print('ctrl-c, leaving ...')
