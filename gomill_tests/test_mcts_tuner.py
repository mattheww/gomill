import random

from gomill import mcts_tuners

def format_parameters(optimiser_parameters):
    """Pretty-print an optimiser parameter vector.

    Returns a string.

    """
    a, b = optimiser_parameters
    return "a: %.3f  b: %.3f" % (a, b)


def test():

    def show():
        print tree.describe()
        print "Best parameter vector: %s" % (
                format_parameters(tree.retrieve_best_parameters()))

    tree = mcts_tuners.Tree(
        dimensions=2,
        subdivisions=3,
        max_depth=5,
        exploration_coefficient=0.5,
        initial_visits=10,
        initial_wins=5,
        parameter_formatter=format_parameters,
        )

    tree.new_root()
    random.seed(12345)

    for i in range(1100):
        simulation = mcts_tuners.Simulation(tree)
        simulation.run()
        simulation.update_stats(candidate_won=random.randrange(2))
    print simulation.get_parameters()

    #show()
    print tree.node_count
    print simulation.choice_path
    print tree.retrieve_best_parameters()
    #print tree.describe()


def stuff():

    simulation = mcts_tuners.Simulation(tree)
    simulation.run()
    assert simulation.choice_path == [3]
    simulation.update_stats(candidate_won=True)

    random.seed()
    simulation = mcts_tuners.Simulation(tree)
    simulation.run()
    assert simulation.choice_path[0] == 3
    print simulation.choice_path
    simulation.update_stats(candidate_won=False)
    #print simulation.get_parameters()
    show()


if __name__ == "__main__":
    test()
