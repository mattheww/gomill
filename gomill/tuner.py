from gomill import cem

BATCH_SIZE = 100

class Sample(object):
    def __init__(self, parameters):
        self.parameters = parameters

    def __str__(self):
        s = " ".join("%5.2f" % f for f in self.parameters)
        return "<sample %s>" % s

def get_sample_fitness(sample):
    # FIXME
    a, b = sample.parameters
    a_fitness = 20 - abs(a - 7.0)
    b_fitness = 20 - abs(b - 6.0)
    return a_fitness + 3 * b_fitness

def get_fitness(parameter_vectors):
    """FIXME

    parameter_vectors -- list of optimiser parameter vectors

    Returns a corresponding list of fitness values (floats)

    Only the rank of the fitness values matters.

    """
    return [get_sample_fitness(Sample(parameters))
            for parameters in parameter_vectors]

def get_initial_distribution():
    # FIXME
    result = cem.Distribution([(10.0, 2.0), (3.0, 1.0)])
    return result

def test():
    optimiser = cem.Cem_optimiser(fitness_fn=get_fitness)
    optimiser.set_distribution(get_initial_distribution())
    print optimiser.run(number_of_generations=20)

if __name__ == "__main__":
    test()
