import numpy as np
import matplotlib.pyplot as plt
import sys
import time

program, MAX_TIME, REDUCTION_FACTOR = sys.argv[0], int(sys.argv[1]), int(sys.argv[2])

# Data Lookup Structures
NEIGHBOR_LIST = {}         # (x,y) -> neighbors of (x,y)
NODE_STATS = {}            # (x,y) -> {"numI": # infected, "nonR": # non_removed}

# Global Model Params
OUT_DIR = "results/"
GRAPH_SIZE = int(np.sqrt(174 - 1)/np.sqrt(REDUCTION_FACTOR))  # sqrt(square area of city) / sqrt(scaling_factor)
NUM_AGENTS = int((1.6 * 10**6)/(REDUCTION_FACTOR))            # population / scaling factor
NUM_NODES = (GRAPH_SIZE + 1)**2
CUR_TIME = 0
NUM_INF = 1
NUM_R = 0
NEW_CASES = 1

# Agent Params
CONSTRAIN_MOVEMENT = False
CONSTRAIN_NETWORK = False
# EXCLUDE_EDGES = {()}
PROB_STAY = 0.9
PROB_LEAVE = 1 - PROB_STAY
INF_TIME = 8.0             # From CDC avg time til death
R_VALUE = 2.0              # From CDC
R0 = R_VALUE / INF_TIME    # Probability of infecting someone per timestep


class Agent(object):
    """ An agent in the Ebola model. """

    def __init__(self, pos, state):
        self.pos = pos
        self.state = state
        self.exposed_time = None
        self.infected_time = None
        self.INC_TIME = np.random.randint(2, 21 + 1) # From WHO incubation time
        self.neighbors = self.find_neighbors()
        # Update stats
        if state == "I":
            NODE_STATS[self.pos]["numI"] += 1
            self.infected_time = CUR_TIME
        if state != "R":
            NODE_STATS[self.pos]["nonR"] += 1

    def update_pos(self):
        # Remove self from stats
        if self.state == "I":
            NODE_STATS[self.pos]["numI"] -= 1
        if self.state != "R":
            NODE_STATS[self.pos]["nonR"] -= 1

        # Move to a neighboring position
        if CONSTRAIN_MOVEMENT and self.state == "I":
            num_neighbors = len(self.neighbors) - 1
            probability_dist = [PROB_STAY]
            for i in range(num_neighbors):
                probability_dist.append(PROB_LEAVE / num_neighbors)
            idx = np.random.choice(
                range(len(self.neighbors)), p=probability_dist)
            self.pos = self.neighbors[idx]
        else:
            idx = np.random.choice(range(len(self.neighbors)))
            self.pos = self.neighbors[idx]

        # Add self to stats
        if self.state == "I":
            NODE_STATS[self.pos]["numI"] += 1
        if self.state != "R":
            NODE_STATS[self.pos]["nonR"] += 1

        # New neighbors
        self.neighbors = self.find_neighbors()

    def update_state(self):
        global NUM_INF
        global NUM_R
        global NEW_CASES
        if self.state == "S":
            z = np.random.random()
            if z < (NODE_STATS[self.pos]["numI"] / NODE_STATS[self.pos]["nonR"]) * R0:
                self.state = "E"
                self.exposed_time = CUR_TIME
        elif self.state == "E":
            if (CUR_TIME - self.exposed_time) >= self.INC_TIME:
                self.state = "I"
                self.infected_time = CUR_TIME
                NUM_INF += 1
        elif self.state == "I":
            if (CUR_TIME - self.infected_time) >= INF_TIME:
                self.state = "R"
                NUM_R += 1
                NUM_INF -= 1
                NEW_CASES += 1

    def find_neighbors(self):
        global NEIGHBOR_LIST
        if self.pos in NEIGHBOR_LIST.keys():
            return NEIGHBOR_LIST[self.pos]
        else:
            n = [self.pos]
            for d in [-1, 1]:
                x1 = self.pos[0] + d
                y1 = self.pos[1]
                if not (x1 < 0 or y1 < 0 or x1 > GRAPH_SIZE or y1 > GRAPH_SIZE):
                    n.append((x1, y1))
                x1 = self.pos[0]
                y1 = self.pos[1] + d
                if not (x1 < 0 or y1 < 0 or x1 > GRAPH_SIZE or y1 > GRAPH_SIZE):
                    n.append((x1, y1))
            NEIGHBOR_LIST[self.pos] = n
            return n

    def __repr__(self):
        return str(self.pos) + str(self.state)


def init_agents():
    agents = []
    agents_per_node = NUM_AGENTS / NUM_NODES
    left_over_agents = NUM_AGENTS - (agents_per_node * NUM_NODES)

    print "agents_per_node", agents_per_node
    print "left_over_agents", left_over_agents

    for x in range(GRAPH_SIZE + 1):
        for y in range(GRAPH_SIZE + 1):

            if (x, y) not in NODE_STATS.keys():
                NODE_STATS[(x, y)] = {"numI": 0.0, "nonR": 0.0}
            if left_over_agents > 0:
                agents.append(Agent((x, y), "S"))
                left_over_agents -= 1

            for a in range(agents_per_node):
                state = "S"
                if x == 0 and y == 0 and a == 0:
                    state = "I"
                agents.append(Agent((x, y), state))

    return agents


def main():
    global CUR_TIME
    global NEW_CASES

    start_time = time.strftime("%Y%m%d_%H%M%S")
    print "Graph size:", GRAPH_SIZE, " Nodes:", NUM_NODES
    print "Num agents:", NUM_AGENTS
    agents = init_agents()
    print "Agents initialized..."

    infected_only = []
    removed_only = []
    infected = []
    new_cases = []

    for t in xrange(MAX_TIME):
        CUR_TIME = t
        if t % 7 == 0:
            new_cases.append(NEW_CASES)
            NEW_CASES = 0
        for a in agents:
            a.update_state()
            a.update_pos()
        print "t =", t, "infected =", NUM_INF + NUM_R
        infected.append(NUM_INF + NUM_R)
        infected_only.append(NUM_INF)
        removed_only.append(NUM_R)


    np.save(get_filename(start_time, "INFECTED_")  + ".npy", infected)
    np.save(get_filename(start_time, "INFCONLY_")  + ".npy", infected_only)
    plt.plot(range(MAX_TIME), infected,color='b')
    plt.plot(range(MAX_TIME), infected_only, color='r')
    plt.title("CONSTRAIN_MOVEMENT = " + str(CONSTRAIN_MOVEMENT))
    plt.savefig(get_filename(start_time, "INFECTED_") + ".svg")
    # plt.show()
    plt.close()

    plt.plot(range(len(new_cases)), new_cases)
    plt.title("New cases, CONSTRAIN_MOVEMENT =" + str(CONSTRAIN_MOVEMENT))
    plt.savefig(get_filename(start_time, "NEWCASE_") + ".svg")
    np.save(get_filename(start_time, "NEWCASE_")  + ".npy", new_cases)
    # plt.show()

def get_filename(timestr, prefix=""):
    """ Returns a filename that incorporates a timestamp and a potential prefix.
        The filename summarizes the parameters of the model. """
    global GRAPH_SIZE
    global OUT_DIR
    return OUT_DIR + "/" + prefix + "size{0:03d}_agents{1}_cm{2}_cn{3}_t{4}".format(GRAPH_SIZE, NUM_AGENTS, CONSTRAIN_MOVEMENT, CONSTRAIN_NETWORK,timestr)


if __name__ == '__main__':
    main()
