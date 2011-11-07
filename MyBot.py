#!/usr/bin/env python
from ants import *
import sys
from operator import itemgetter, attrgetter
from collections import deque
from numpy import array
import Ant


isDebug = True # Debug Flag to toggle Debug Output into "debug.txt". Has to been False for submitting!


class Food:
	def __init__(self, pLoc):
		self.loc = (-1, -1)
		self.comingAnt = None
		self.loc = pLoc
		self.usedForFoodRecalc = False
		self.foods = [] #(loc:dist) to all other known food positions
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
	# 4: hill defending field
	rememberedMap = []

	def __init__(self):
		self.turnnumber = 0
		self.mapAspect = 4.2
		self.enemyHills = [] # remembered locations of detected enemy hills
		self.foods = {}
		self.soonOccupied = set() # keep track of what locations will be occupied by ants next round
		self.antList = []
		self.debugOrderCounter = {'1':0, '2':0, '3':0, '4':0, '5':0} # keep track how orders are distributed
		if isDebug:
			f = open('debug.txt', 'w')
			f.close()
		self.maxCPULoad = [-1, -1] # (round, runtime),
		self.mapNeighbours = {} # keeps a list of adjacent map locations to speed up A*
		self.AntCenter=array([-1,-1])
		self.AntVelo=array([-1,-1])
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
				if currVal > maxNew and loc != (rowPos % ants.rows, colPos % ants.cols) and self.rememberedMap[rowPos % ants.rows][colPos % ants.cols] != 3 and self.rememberedMap[rowPos % ants.rows][colPos % ants.cols] != 4:
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
		if loc in ants.my_hills():
			return True
		if self.rememberedMap[loc[0]][loc[1]] == 3 : # water
			return True
		if self.rememberedMap[loc[0]][loc[1]] == 4 : #own ant defending
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
	def sortedInsert(self, list, ins):
		if not list:
			list.append(ins)
			return list
		else:
			for i in range(len(list)):
				if ins[1] < list[i][1]:
					list.insert(i, ins)
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
		self.debugOrderCounter['5'] = 0
		self.debugOrderCounter['6'] = 0

		# if self.turnnumber in [1,14,61]:
			# self.debugPrint("wall: "+str(self.rememberedMap[9][65]))

		time1 = time.clock()

		# clear the housekeeping sets
		self.soonOccupied.clear()

#		for ant in self.antList:
#			self.debugPrint(ant.orderName)

		# check if saved enemy hills are still there
		for hill in [a for a in self.enemyHills if ants.visible(a[0]) and a not in ants.enemy_hills()]:
			self.enemyHills.remove(hill)
			# ants attacking that hill are now free again
			for ant in [a for a in self.antList if a.getTarget() == hill[0] and a.orderName == '2']:
				ant.cancelOrder()
				ant.isAttacking = False

		# update list of enemy hills if new ones become visible
		for hill in [a for a in ants.enemy_hills() if a not in self.enemyHills]: 
			self.enemyHills.append(hill)

		# remove eaten food
		for eatenFoodLoc in [a for a in self.foods if ants.visible(a) and a not in ants.food()]:
			# check in case food got eaten by enemy ant or accidentally
			if self.foods[eatenFoodLoc].hasComingAnt() and self.foods[eatenFoodLoc].comingAnt.orderName == "1":
				self.foods[eatenFoodLoc].comingAnt.cancelOrder()
			# clear distances
			for otherFoodLoc in [a for a in self.foods if a != eatenFoodLoc]: 
				deletingDist = ants.distance(eatenFoodLoc, otherFoodLoc)
				self.foods[otherFoodLoc].foods.remove((eatenFoodLoc, deletingDist))
			del self.foods[eatenFoodLoc]

		# new food visible
		for newFoodLoc in [a for a in ants.food() if a not in self.foods]:
			self.foods[newFoodLoc] = Food(newFoodLoc)

			#add distances to other known foods
			for otherFoodLoc in [a for a in self.foods if a != newFoodLoc]: 
				dist = ants.distance(newFoodLoc, otherFoodLoc)
				self.sortedInsert(self.foods[newFoodLoc].foods, (otherFoodLoc, dist))
				self.sortedInsert(self.foods[otherFoodLoc].foods, (newFoodLoc, dist))

		#update the map
		for row in range(0, ants.rows):
			rowString = ""
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
				rowString += str(self.rememberedMap[row][col])	
#			self.debugPrint(rowString.replace('-1', 'X'))
		#add newborn ants to antlist				
		for locAntNewborn in [a for a in ants.my_hills() if not a in self.antList]:
				if not ants.unoccupied(locAntNewborn):
					newAnt = Ant.Ant(locAntNewborn)
					self.debugPrint("newAnt: " + str(newAnt))
					self.antList.append(newAnt)

		# remove killed ants ;(
		aliveAntsLoc = set(ants.my_ants())
		for ant in [a for a in self.antList if a.loc not in aliveAntsLoc]:
			self.debugPrint("killedAnt: " + str(ant))
			self.antList.remove(ant)		
			#add the field as movable again
			if ant.orderName == '5':
				self.rememberedMap[ant.loc[0]][ant.loc[1]] = 0 			
				for neigh in self.mapNeighbours[ant.loc]:
					self.mapNeighbours[neigh].append(ant.loc)						

		
		
		#calc center and velocity of ants
		self.AntCenter=array([0,0])
		self.AntVelo=array([0,0])
		for ant in self.antList:
			if not ant.orderName=='5':
				self.AntCenter+=ant.loc
				self.AntVelo+=ant.velo
			
		nAnts=len(self.antList)
#		self.AntVelo=self.AntVelo/nAnts
#		self.AntCenter=self.AntCenter/nAnts
#		
		if nAnts>0:
			self.debugPrint("Center of ants:\t"+str(self.AntCenter/nAnts))
			self.debugPrint("Avg. Velo of ants:\t"+str(self.AntVelo/nAnts))
		
#		for ant in [a for a in self.antList if a.orderName==5]:
#			if ant.loc==ant.target:
#				self.knownMap[ant.loc[0]][ant.loc[1]]=4
		time2 = time.clock()
		# priority 1: Gather every food item by closest ant
		foodDistances = []	
		for foodLoc in [f for f in self.foods]:
			for ant in [a for a in self.antList if not a.orderName == '5']:
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
			if len(self.foods) > 1 and len(self.antList) > 1:
				foodNeigh = self.foods[ activeFood.foods[0][0] ]
				isFoodNeighTargeted = foodNeigh.hasComingAnt()
				if isFoodNeighTargeted:
					distA2F2 = ants.distance(activeAnt.loc, dist[2]) #from potential ant to potential food
					distA1F1 = ants.distance(foodNeigh.loc, foodNeigh.comingAnt.loc) #from food Neighbour to its coming ant
					distF1F2 = ants.distance(dist[2], foodNeigh.loc) #from potential food to neighbour food
					if distA2F2 >= (distA1F1 + distF1F2):
						isSkipBecauseTime = True
			
			# hasn't been used + order hasn't already been given
			if not activeFood.usedForFoodRecalc and not activeAnt.usedForFoodRecalc and activeFood.comingAnt != activeAnt and not isSkipBecauseTime:
				# food already had an incoming ant
				if activeFood.hasComingAnt() and activeFood.comingAnt.orderName == "1":
					activeFood.comingAnt.cancelOrder()
					activeFood.comingAnt = None
				
				# ant was already targeting food
				if activeAnt.hasTarget() and activeAnt.orderName == "1":
					target_of_ant = activeAnt.target
					targets_coming_ant = self.foods[target_of_ant].comingAnt
					targets_coming_ant.cancelOrder()
					self.foods[target_of_ant].comingAnt = None
					
				activeAnt.tryOrder(dist[2], ants, '1', self)
				activeFood.comingAnt = activeAnt
				activeFood.usedForFoodRecalc = True
				activeAnt.usedForFoodRecalc = True
			# order has already been given -> mark as used
			elif activeFood.comingAnt == activeAnt:
				activeAnt.usedForFoodRecalc = True
				activeFood.usedForFoodRecalc = True
		time3 = time.clock()
		
		
		
		# priority 2: attack enemy hills. 50% of closest ants are sent to attack
		
		for hill in self.enemyHills:
			attackDistances = []
			for ant in [a for a in self.antList if not a.hasTarget()]:
				dist_temp = ants.distance(hill[0], ant.loc)
				attackDistances.append((dist_temp, ant, hill[0]))
			attackDistances.sort(key=itemgetter(0, 2))
			numberOfAttackAnts = int(round(0.5 * len(ants.my_ants())))	
			numberOfAttackingAnts = len([i for i in self.antList if i.isAttacking])
			for i in [j for j in range(numberOfAttackAnts) if (len(attackDistances) - numberOfAttackingAnts) >= (j + 1)]: # 50%
				attackDistances[i][1].tryOrder(attackDistances[i][2], ants, '2', self)
				attackDistances[i][1].isAttacking = True
			
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
		
		time4 = time.clock()
		
		
		#experimental: build 8-ant cage
		if(len(self.antList) > 10+10*len(ants.my_hills())):
			for hill in ants.my_hills():
				targetLocs = []
			
				targetLocs.append(((hill[0] + 2) % ants.rows, (hill[1] + 1) % ants.cols))
				targetLocs.append(((hill[0] + 2) % ants.rows, (hill[1] - 1) % ants.cols))
				targetLocs.append(((hill[0] - 2) % ants.rows, (hill[1] + 1) % ants.cols))
				targetLocs.append(((hill[0] - 2) % ants.rows, (hill[1] - 1) % ants.cols))
				targetLocs.append(((hill[0] + 1) % ants.rows, (hill[1] + 2) % ants.cols))
				targetLocs.append(((hill[0] + 1) % ants.rows, (hill[1] - 2) % ants.cols))
				targetLocs.append(((hill[0] - 1) % ants.rows, (hill[1] + 2) % ants.cols))
				targetLocs.append(((hill[0] - 1) % ants.rows, (hill[1] - 2) % ants.cols))
				
				for ant in [a for a in self.antList if a.loc == hill if not a.hasTarget()]:
					
					notUsed = [a for a in targetLocs if not (self.rememberedMap[a[0]][a[1]] == 4 or self.rememberedMap[a[0]][a[1]] == 3)]
#					self.debugPrint(notUsed)
					if notUsed:
						ant.tryOrder(notUsed[0], ants, '5', self)
						self.rememberedMap[notUsed[0][0]][notUsed[0][1]] = 4						
						for neigh in self.mapNeighbours[notUsed[0]]:
							if notUsed[0] in self.mapNeighbours[neigh]:
								self.mapNeighbours[neigh].remove(notUsed[0])						
					
					
#					for defend in defendDistances:
#							if defend[2] not in used  and not defend[1].hasTarget() and not self.knownMap[defend[2][0]][defend[2][1]]==4:
#								defend[1].tryOrder(defend[2], ants, '5', self)
#								used.append(defend[2])
#								self.knownMap[defend[2][0]][defend[2][1]]=4
#						
						
				
		
#		 priority 3: Freshly created ants. Move away from hill into random direction
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
		
		
		
	#	 priority 6: Explore the map
		nExplorers=len([a for a in self.antList if a.isExploring])
		for ant in [a for a in self.antList if not a.hasTarget()]:
			if(nExplorers<5):
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
					ant.tryOrder(targetNew, ants, "6", self)
					ant.isExploring=True
					nExplorers+=1
			
	
		time5 = time.clock()
		
		
		
	
	#rest of the ants do some flocking behaviour
		if(nAnts>1):
			for ant in [a for a in self.antList if not a.hasTarget()]:
				ant.boidMove(self,ants,nAnts)
	
	
		
		time6 = time.clock()
		self.debugPrint("flocking time: "+str((time6-time5)*1000))
		for ant in [a for a in self.antList if a.hasTarget or a.orderName == '4']:
			ant.move(ants, self)
		
		time7 = time.clock()
		
		self.debugPrint("time used: " + str(int(1000 * (time.clock() - ants.turn_start_time))) + "ms")
		if int(1000 * (time.clock() - ants.turn_start_time)) > self.maxCPULoad[1]:
			self.maxCPULoad[1] = 1000 * (time.clock() - ants.turn_start_time)
			self.maxCPULoad[0] = self.turnnumber
			self.debugPrint("new maxCPULoad: " + str(self.maxCPULoad))
			
			self.debugPrint("time update: " + str(1000 * (time2 - time1)))
			self.debugPrint("time p1: " + str(1000 * (time3 - time2)))
			self.debugPrint("time p2: " + str(1000 * (time4 - time3)))
			self.debugPrint("time p3: " + str(1000 * (time5 - time4)))
			self.debugPrint("time p4: " + str(1000 * (time6 - time5)))
			self.debugPrint("time rest: " + str(1000 * (time7 - time6)))
			
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
