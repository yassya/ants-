#!/usr/bin/env python
from ants import *
import sys
#from operator import itemgetter, attrgetter
from collections import deque
import Ant
import colorsys
from copy import *
import gc

isDebug = True # Debug Flag to toggle Debug Output into "debug.txt". Has to been False for submitting!
isDebugDraw = True # see isDraw_* commands
isDebugDrawOrderinfo = False # slow!

class Food:
	def __init__(self, pLoc, bot, ants):
		self.loc = pLoc
		self.bfs = None
		self.cameFrom = None
		self.generateBFS(bot, ants)
	def __repr__(self):
		return repr(self.loc)
	def generateBFS(self, bot, ants):
		self.camefrom = {}
		bfsOpenSet = deque(  )
		bfsOpenSet.append( (self.loc, 0) )
		self.bfs = dict()
		self.bfs[ self.loc ] = 0
		
		antsReachedTarget = min(2, len(bot.antList))
		antsReached = 0
		dblset = set()
		if bfsOpenSet:
			bfsOpenSetPop = [ [-1,-1], -1 ] #dummy
			while bfsOpenSet and not ( bfsOpenSetPop[1]>20 or antsReached >= antsReachedTarget ):
				bfsOpenSetPop = bfsOpenSet.popleft()
				for nLoc in bot.mapNeighbours[ bfsOpenSetPop[0] ]:
					if nLoc not in self.bfs and nLoc not in dblset and bot.rememberedMap[ nLoc[0] ][ nLoc[1] ] != -1:
						self.bfs[ nLoc ] = bfsOpenSetPop[1]+1
						self.camefrom[ nLoc ] = bfsOpenSetPop[0]
						bfsOpenSet.append( (nLoc, bfsOpenSetPop[1]+1) )
						dblset.add( nLoc )
						if nLoc in ants.my_ants():							
							antsReached += 1
								
	def debugPrint(self, msg):
		if isDebug:
			f = open('debug.txt', 'a')
			f.write(str(msg) + "\n")
			f.close()
			
class MyBot:
	# -1: still unknown
	# 0: free or own ant
	# 3: water
	# 4: hill defending field
	rememberedMap = []

	def __init__(self):
		self.turnnumber = 0
		self.enemyHills = []
		self.foods = {}
		self.soonOccupied = set() # keep track of what locations will be occupied by ants next round
		self.antList = dict()
		if isDebug:
			f = open('debug.txt', 'w')
			f.close()
		self.mapNeighbours = {} # keeps a list of adjacent map locations to speed up A*
		self.mapNeighboursFull = {}
		
		self.bfsExploredTotal = {}
		self.borderTotal = set()
		self.borderTotalFree = set()
		
		self.currentBorder = dict()
		self.currentBorderFree = set()
		
		self.oneAntBorder = None
		self.oneAntVision = None
		self.oneAntVisionWOF = None
		
		self.vision = None
		self.vision_offsets_2 = None
		
	def do_setup(self, ants):
		self.rememberedMap = [[-1 for col in range(ants.cols)]
			for row in range(ants.rows)]
		
		# fill mapNeighbours
		for row in range(0, ants.rows):
			for col in range(0, ants.cols):
				loc = row, col
				l = []
				l.append(ants.destination(loc, 'n'))
				l.append(ants.destination(loc, 'e'))
				l.append(ants.destination(loc, 's'))
				l.append(ants.destination(loc, 'w'))
				self.mapNeighbours[loc] = l
				self.mapNeighboursFull[loc] = copy( l ) # all neighbours, even with blocked ones
		
		# precalculate vision radius of one ant (oneAntVision), its border (oneAntBorder), and the difference (oneAntVisionWOF) for faster "explore" and "reexplore" orders
		self.viewradius = int(sqrt(ants.viewradius2))
		startPos = ( self.viewradius+1, self.viewradius+1 )
		self.oneAntVision = [ startPos ]
		self.oneAntBorder = []
		bfsOpenDeque = deque()
		bfsOpenDeque.append( startPos )
		
		dblset = set( bfsOpenDeque )
		if bfsOpenDeque:
			bfsOpenDequePop = True #dummy
			while bfsOpenDeque:
				bfsOpenDequePop = bfsOpenDeque.popleft()
				isBorder = False
				for nLoc in self.mapNeighbours[ bfsOpenDequePop ]:
					dx = nLoc[0]-startPos[0]
					dy = nLoc[1]-startPos[1]
					d2 = dx*dx + dy*dy
					if d2<ants.viewradius2 and nLoc not in dblset:
						dblset.add( nLoc )
						self.oneAntVision.append( (nLoc[0], nLoc[1]) )
						bfsOpenDeque.append( nLoc )
					elif not d2<ants.viewradius2:
						isBorder = True
				if isBorder:
					self.oneAntBorder.append( (bfsOpenDequePop[0], bfsOpenDequePop[1]) )
		
		for i in self.oneAntVision:
			idx = self.oneAntVision.index( i )
			self.oneAntVision[ idx ] = (i[0]-startPos[0], i[1]-startPos[1])
		for i in self.oneAntBorder:
			idx = self.oneAntBorder.index( i )
			self.oneAntBorder[ idx ] = (i[0]-startPos[0], i[1]-startPos[1])
		
		self.oneAntVisionWOF = deepcopy( self.oneAntVision )
		removeSet = set()
		for i in self.oneAntVisionWOF:
			if i in self.oneAntBorder:
				removeSet.add( i )
		for i in removeSet:
			self.oneAntVisionWOF.remove( i )

	def debugPrint(self, msg, newline=True):
		if isDebug:
			f = open('debug.txt', 'a')
			if newline:
				f.write(str(msg) + "\n")
			else:
				f.write(str(msg))
			f.close()

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
		# elif not ants.unoccupied(loc): # ant
		elif loc in self.antList:
			# if self.antList[loc].activeOrder != None and self.antList[loc].activeOrder.path[0]
			return True
		else:
			return False
	
	# resolve order conflicts
	# if a target is being targeted by more than one ant, the order is only given to ant with highest value. Order will be removed from other ants, making them use the next best. Only resolve only one conflicted target at a time, because resolving may lead to new conflicts
	def resolveConflictedOrders(self):
		while True:
			orderTargets = dict() #target:ant
			conflictingOrderAnts = []
			conflictingOrderTarget = None
			
			for ant in [self.antList[a] for a in self.antList if self.antList[a].orders]:
				if ant.orders[0].ordername in ["food", "explore", "reexplore"]:
					antTarget = ant.orders[0].target
					antValue = ant.orders[0].value
					if antTarget in orderTargets:
						if conflictingOrderTarget == None:
							conflictingOrderTarget = antTarget
							conflictingOrderAnts.append( (antValue, ant) )
							firstAnt = orderTargets[antTarget]
							conflictingOrderAnts.append( (firstAnt.orders[0].value, firstAnt) )
						elif antTarget == conflictingOrderTarget:
							conflictingOrderAnts.append( (antValue, ant) )
					else:
						orderTargets[ antTarget ] = ant
			
			if conflictingOrderAnts:
				conflictingOrderAnts.sort( reverse=True )
				bestOrderAnt = conflictingOrderAnts[0][1]
				for switchAnt in [ant[1] for ant in conflictingOrderAnts if ant[1] != bestOrderAnt]:
					switchAnt.orders.pop(0)
			else:
				break
	
	# uses each food's own BFS to calculate orders to every ant within that BFS
	def ordersFood(self, ants):		
		for food in [self.foods[foodLoc] for foodLoc in self.foods]:
			for ant in [self.antList[antLoc] for antLoc in self.antList]:
				if ant.loc in food.bfs:					
					dist = food.bfs[ ant.loc ]
					path = deque()
					path.append( food.camefrom[ ant.loc ] )
					while path[-1] != food.loc:
						pos = path[-1]
						path.append( food.camefrom[ pos ] )
					order = Ant.Order(dist, 40, food.loc, "food", path)
					ant.orders.append( order )
					if isDebugDrawOrderinfo:
						iStr = str( order.ordername)+"_"+str( round(order.value, 1))
						print("i "+str(ant.loc[0])+" "+str(ant.loc[1])+" "+iStr )
		
	# def combineOrders(self, ants):	
		# for ant in [self.antList[a] for a in self.antList if self.antList[a].orders[0][3] == "food"]:
			# self.bfsExplore = [[-1 for col in range(ants.cols)]
				# for row in range(ants.rows)]
			# bfsOpenSet = deque()
			# seed = ant.orders[0][2]
			# bfsOpenSet.append( (seed, 0) )
			# self.bfsExplore[ seed[0] ][ seed[1] ] = 0
			
			# if bfsOpenSet:
				# bfsOpenSetPop=[-1,-1]
				# while bfsOpenSetPop[1]<50 and bfsOpenSet:
					# bfsOpenSetPop = bfsOpenSet.popleft()
					# for nLoc in self.mapNeighbours[ bfsOpenSetPop[0] ]:
						# if self.bfsExplore[ nLoc[0] ][ nLoc[1] ] == -1:
							# self.bfsExplore[ nLoc[0] ][ nLoc[1] ] = bfsOpenSetPop[1]+1
							# bfsOpenSet.append( (nLoc, bfsOpenSetPop[1]+1) )
							# if nLoc in self.foods:
								# if nLoc in [order[2] for order in ant.orders]:
									# extraTime = bfsOpenSetPop[1]+1
									# combinedTime = ant.orders[0][2]
									# self.debugPrint("found first order. ant: "+str(ant.loc)+", food: "+str(nLoc))
								# # dist = bfsOpenSetPop[1]+1
								# # direction = bfsOpenSetPop[0]
								# # self.antList[nLoc].orders.append( (20.0/dist, direction, foodLoc, "food") )
								# # antPerFoodCount += 1
	
	# generates the border of the currently seen territory. BFS from there to "re-explore" the map
	def ordersReExplore(self, ants):
		# fill visible terrain and its border by overlaying each ants vision/"vision-1"
		timeBlast0 = time.clock()
		self.bfsExplored = set()
		self.currentBorder = set()
		for ant in ants.my_ants():
			a_row, a_col = ant
			for v_row, v_col in self.oneAntVision:
				l = (a_row+v_row)%ants.rows, (a_col+v_col)%ants.cols
				self.bfsExplored.add( l )
			for v_row, v_col in self.oneAntVisionWOF:
				l = (a_row+v_row)%ants.rows, (a_col+v_col)%ants.cols
				self.currentBorder.add( l )
		self.currentBorder = self.bfsExplored - self.currentBorder
		
		# remove currentBorder points which are on water
		removeSet = set()
		for f in self.currentBorder:
			if self.rememberedMap[ f[0] ][ f[1] ] == 3:
				removeSet.add( f )
		for i in removeSet:
			self.currentBorder.remove( i )
		
		# calculate all future positions of all ants
		borderBlastPoints = set()
		for ant in [self.antList[a] for a in self.antList if self.antList[a].activeOrder!=None]:
			for waypoint in ant.activeOrder.path:
				borderBlastPoints.add( waypoint )
		
		# orderVicinity = set()
		# for ant in [self.antList[a] for a in self.antList if self.antList[a].activeOrder!=None]:
			# for waypoint in ant.activeOrder.path:
				# o_row, o_col = waypoint
				# for v_row, v_col in self.oneAntVision:
					# l = (o_row+v_row)%ants.rows, (o_col+v_col)%ants.cols
					# orderVicinity.add( l )
		
		# remove vicinity of these points from the current border
		self.currentBorderFree = copy( self.currentBorder )
		for f in self.currentBorder:
			for cmp in borderBlastPoints:
				dx = cmp[0]-f[0]
				dy = cmp[1]-f[1]
				if dx*dx+dy*dy <= ants.viewradius2:
					self.currentBorderFree.remove( f )
					break
		
		# self.currentBorderFree -= orderVicinity
		cpuCmp = round( 1000*( time.clock() - timeBlast0), 2)
		self.debugPrint("reexplore: visibility + blast: "+str( cpuCmp ))
		
		# BFS from Border
		timeExp0 = time.clock()
		self.bfsExplored3 = {}
		camefrom = {}
		bfsOpenDeque = deque()
		for f in self.currentBorderFree:
			if self.rememberedMap[ f[0] ][ f[1] ] != 3:
				bfsOpenDeque. append( (f, 0) )
				self.bfsExplored3[ f ] = 0

		if bfsOpenDeque:
			bfsOpenDequePop = True #dummy
			while bfsOpenDeque:
				bfsOpenDequePop = bfsOpenDeque.popleft()
				for nLoc in self.mapNeighbours[ bfsOpenDequePop[0] ]:
					if nLoc not in self.bfsExplored3 and ants.visible( nLoc):
						self.bfsExplored3[ nLoc ] = bfsOpenDequePop[1]+1
						camefrom[ nLoc ] = bfsOpenDequePop[0]
						bfsOpenDeque.append( (nLoc, bfsOpenDequePop[1]+1) )
						if nLoc in ants.my_ants():
							dist = bfsOpenDequePop[1]+1
							path = deque()
							path.append( camefrom[ nLoc ] )
							while path[-1] not in self.currentBorderFree:
								pos = path[-1]
								path.append( camefrom[ pos ] )
							self.antList[nLoc].orders.append( Ant.Order(dist, 10, path[-1], "reexplore", path) )
							if isDebugDrawOrderinfo:
								iStr = str( order.ordername)+"_"+str( round(order.value, 1))
								print("i "+str(nLoc[0])+" "+str(nLoc[1])+" "+iStr )
		
		cpuExp = round( 1000*( time.clock()-timeExp0 ), 2)
		self.debugPrint("reexplore: expand: "+str( cpuExp ))
		
	# generates the border of the total seen territory. BFS from there to push the border
	def ordersExplore(self, ants):
		# explore-BFS is cumulative: Each round, it only expands newly discovered terrain from the fringe. that part is fast!
		timeCmp0 = time.clock()
		bfsOpenDeque = deque( )
		if self.turnnumber == 1:
			for ant in [self.antList[a] for a in self.antList]:
				self.bfsExploredTotal[ ant.loc ] = 0
				bfsOpenDeque.append( ant.loc )
		else:
			bfsOpenDeque = copy( deque( self.borderTotal ) )
			self.borderTotal = set()
		
		dblset = set( bfsOpenDeque )
		if bfsOpenDeque:
			bfsOpenDequePop = True #dummy
			while bfsOpenDeque:
				bfsOpenDequePop = bfsOpenDeque.popleft()						
				isBorder = False
				for nLoc in self.mapNeighbours[ bfsOpenDequePop ]:
					if self.rememberedMap[ nLoc[0] ][ nLoc[1] ] == -1:
						isBorder = True
					if nLoc not in self.bfsExploredTotal and self.rememberedMap[ nLoc[0] ][ nLoc[1] ] != -1 and nLoc not in self.borderTotal:
						self.bfsExploredTotal[ nLoc ] = 0
						if nLoc not in dblset:
							bfsOpenDeque.append( nLoc )
							dblset.add( nLoc )
				if isBorder:
					self.borderTotal.add( bfsOpenDequePop )
					self.bfsExploredTotal[ bfsOpenDequePop ] = -1
		
		# calculate all future positions of all ants
		borderPoints = set()
		for ant in [self.antList[a] for a in self.antList if self.antList[a].activeOrder!=None]:
			for waypoint in ant.activeOrder.path:
				borderPoints.add( waypoint )
		
		# remove vicinity of these points from the current border
		self.borderTotalFree = copy( self.borderTotal )
		for f in self.borderTotal:
			for cmp in borderPoints:
				dx = cmp[0]-f[0]
				dy = cmp[1]-f[1]
				if dx*dx+dy*dy <= ants.viewradius2:
					self.borderTotalFree.remove( f )
					break
		cpuCmp = round( 1000*( time.clock()-timeCmp0), 2)
		self.debugPrint("explore BFS+border blast: "+str( cpuCmp ))
		
		
		# BFS inward from borderTotalFree. Goes over full map every time -> slow
		timeExp0 = time.clock()
		self.bfsExploredTotal = {}
		camefrom = {}
		bfsOpenDeque = deque()
		for f in self.borderTotalFree:
			bfsOpenDeque. append( (f, 0) )
			self.bfsExploredTotal[ f ] = 0

		if bfsOpenDeque:
			bfsOpenDequePop = True #dummy
			while bfsOpenDeque:
				bfsOpenDequePop = bfsOpenDeque.popleft()
				for nLoc in self.mapNeighbours[ bfsOpenDequePop[0] ]:
					if nLoc not in self.bfsExploredTotal and self.rememberedMap[ nLoc[0] ][ nLoc[1] ] != -1:
						self.bfsExploredTotal[ nLoc ] = bfsOpenDequePop[1]+1
						camefrom[ nLoc ] = bfsOpenDequePop[0]
						bfsOpenDeque.append( (nLoc, bfsOpenDequePop[1]+1) )
						if nLoc in ants.my_ants():
							dist = bfsOpenDequePop[1]+1
							path = deque()
							path.append( camefrom[ nLoc ] )
							while path[-1] not in self.borderTotalFree:
								pos = path[-1]
								path.append( camefrom[ pos ] )
							order = Ant.Order(dist, 30, path[-1], "explore", path)
							self.antList[nLoc].orders.append( order )
							if isDebugDrawOrderinfo:
								iStr = str( order.ordername)+"_"+str( round(order.value, 1))
								print("i "+str(nLoc[0])+" "+str(nLoc[1])+" "+iStr )
		
		cpuExp = round( 1000*( time.clock()-timeExp0 ), 2)
		self.debugPrint("explore expand: "+str( cpuExp ))
	
	# high Value order to flee from potential death
	def ordersSurvive(self, ants):
		for eAnt in ants.enemy_ants():
			eAntLoc = eAnt[0]
			for ant in [self.antList[a] for a in self.antList if self.antList[a].orders]:
				fAntLoc = ant.activeOrder.path[0]
				antLoc = ant.loc
				fDist = ants.distance( fAntLoc, eAntLoc )
				if fDist <= 4:
					dist = ants.distance( antLoc, eAntLoc )
					fleeDirection = random.choice( ants.direction( eAntLoc, antLoc ) )
					fleeDestination = ants.destination( antLoc, fleeDirection )
					path = deque( )
					path.append( fleeDestination )
					order = Ant.Order(dist, 100, fleeDestination, "survive", path)
					ant.orders.append( order )
	
	# draw orders, BFS's and borders
	def debugDraw(self, ants):
		isDraw_bfsExploredTotal = False
		isDraw_borderTotal = True
		isDraw_currentBorder = False
		isDraw_orderArrows = True
		
		# draw explore BFS
		if isDraw_bfsExploredTotal:
			for field in self.bfsExploredTotal:
				bfsValue = self.bfsExploredTotal[ field ]
				color = colorsys.hsv_to_rgb( (0.05*bfsValue)%1.0, 1.0, 1.0)
				print("v setFillColor "+str( int(color[0]*255) )+" "+str(int(color[1]*255))+" "+str(int(color[2]*255))+" 0.2")
				print("v tile "+str(field[0])+" " + str(field[1]) )
		
		# reexplore border
		if isDraw_currentBorder:
			for f in self.currentBorder:
				if f in self.currentBorderFree:
					print("v setFillColor 0 0 200 0.6")
				else:
					print("v setFillColor 0 250 0 0.4")
				print("v tile "+str(f[0])+" " + str(f[1]) )
		
		# explore border
		if isDraw_borderTotal:
			for f in self.borderTotal:
				if f in self.borderTotalFree:
					print("v setFillColor 255 255 255 0.6") # white
				else:
					print("v setFillColor 20 20 20 0.6") # black
				print("v tile "+str(f[0])+" " + str(f[1]) )
		
		# order arrows
		if isDraw_orderArrows:
			for ant in [self.antList[a] for a in self.antList if self.antList[a].activeOrder != None]:
				if ant.activeOrder.ordername == "food":
					print("v setLineColor 255 255 255 0.8") # white
				elif ant.activeOrder.ordername == "explore":
					print("v setLineColor 100 255 100 0.8") # green
				elif ant.activeOrder.ordername == "reexplore":
					print("v setLineColor 255 50 50 0.8") # red
				elif ant.activeOrder.ordername == "survive":
					print("v setLineColor 255 255 50 0.8") # yellow
				
				target = ant.activeOrder.target
				print( "v arrow "+str( ant.loc[0] )+" "+str( ant.loc[1] )+" "+str( target[0] )+" "+str( target[1] ) )
	
	# update mapNeighbours and rememberedMap
	def updateMap(self, ants):
		for row in range(0, ants.rows):
			for col in range(0, ants.cols):
				loc = row, col
				if ants.vision[row][col]:
					if not ants.passable(loc):
						if self.rememberedMap[row][col] != 3:
							for neigh in self.mapNeighbours[loc]:
								self.mapNeighbours[neigh].remove(loc)
							self.rememberedMap[row][col] = 3
					else:
						self.rememberedMap[row][col] = 0	
	
	def do_turn(self, ants):
		self.turnnumber += 1
		self.debugPrint("\nTURN " + str(self.turnnumber))
		ants.visible( (0,0) ) #initialize ants.vision
	
		# clear the housekeeping sets
		timeUpdate0 = time.clock()
		self.soonOccupied.clear()

		# update self.enemyHills
		for hill in [a for a in self.enemyHills if ants.visible(a[0]) and a not in ants.enemy_hills()]:
			self.enemyHills.remove( hill )
		for hill in [a for a in ants.enemy_hills() if a not in self.enemyHills]: 
			self.enemyHills.append( hill )
		
		# check if ants reached target
		for ant in [self.antList[a] for a in self.antList]:
			if ant.activeOrder!= None and ant.activeOrder.ordername in ["explore", "reexplore", "survive"] and ant.activeOrder.target == ant.loc:
				ant.activeOrder = None
		
		self.updateMap( ants )
		
		#add newborn ants to antlist				
		for locAntNewborn in [a for a in ants.my_hills() if not a in self.antList]:
				if not ants.unoccupied(locAntNewborn):
					newAnt = Ant.Ant(locAntNewborn)
					self.debugPrint("newAnt: " + str(newAnt))
					self.antList[locAntNewborn] = newAnt

		# remove killed ants ;(
		#aliveAntsLoc = set( ants.my_ants() )
		for ant in [a for a in self.antList if a not in ants.my_ants()]:
			self.debugPrint("killed: " + str(ant))
			del self.antList[ant]
		
		# new food
		timeFoodA0 = time.clock()
		for newFoodLoc in [a for a in ants.food() if a not in self.foods]:
			self.foods[ newFoodLoc ] = Food(newFoodLoc, self, ants)
		
		# remove food
		for eatenFoodLoc in [a for a in self.foods if ants.visible(a) and a not in ants.food()]:
			for ant in [self.antList[a] for a in self.antList]:
				if ant.activeOrder!= None and ant.activeOrder.ordername=="food" and ant.activeOrder.target == eatenFoodLoc:
					ant.activeOrder = None
			del self.foods[ eatenFoodLoc ]
		CpuFood = round( 1000* ( time.clock() - timeFoodA0 ), 1)
		
		# clear ant orders
		for ant in [self.antList[a] for a in self.antList]:
			ant.orders = []
			if ant.activeOrder != None:
				ant.orders.append( ant.activeOrder )
		
		CpuUpdate = round( 1000* ( time.clock() - timeUpdate0 ), 1)
			
		# BFS food
		timeFood0 = time.clock()
		self.ordersFood(ants)
		CpuFood += round( 1000* ( time.clock() - timeFood0 ), 1)
		
		# sort and evaluate orders
		for ant in [self.antList[a] for a in self.antList if self.antList[a].orders]:
			ant.evalOrders()
			ant.activeOrder = ant.orders[0]
		
		# BFS explore
		timeExp0 = time.clock()
		self.ordersExplore(ants)
		self.ordersReExplore(ants)
		CpuExp = round( 1000* ( time.clock() - timeExp0 ), 2)
		
		for ant in [self.antList[a] for a in self.antList if self.antList[a].orders]:
			ant.evalOrders()
			ant.activeOrder = ant.orders[0]
		
		timeResolve0 = time.clock()
		self.resolveConflictedOrders()
		timeResolve1 = time.clock()
		CpuResolve = round( 1000*( timeResolve1-timeResolve0 ), 2)
		
		self.ordersSurvive(ants)
		
		for ant in [self.antList[a] for a in self.antList if self.antList[a].orders]:
			ant.evalOrders()
			ant.activeOrder = ant.orders[0]
		
		# combine orders
		# timeCombine0 = time.clock()
		# self.combineOrders(ants)
		# timeCombine1 = time.clock()
		# CpuCombine = round( 1000* ( timeCombine1 - timeCombine0 ), 1)
		# self.debugPrint("CpuCombine: "+str( CpuCombine ))
		
		
		# debug drawings
		timeDebug0 = time.clock()
		if isDebugDraw and self.turnnumber in range(1,100):
			self.debugDraw( ants )
		cpuDebug = round( 1000*( time.clock() - timeDebug0 ), 2)
		
		# execute orders
		for ant in [self.antList[a] for a in self.antList]:
			ant.move(ants, self)
		
		# cpu debug prints
		CpuTotal = round( 1000 * (time.clock() - ants.turn_start_time), 1)
		self.debugPrint("CPU total: " + str(CpuTotal)+", Update: "+str(CpuUpdate) + ", food: "+str(CpuFood)+", Resolve: "+str(CpuResolve)+", explore: "+str(CpuExp)+", debug: "+str( cpuDebug ))
			
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
