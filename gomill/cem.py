"""Cross-entropy parameter tuning."""

from random import gauss
from math import sqrt

def square(f):
    return f * f

class Distribution(object):
    """A multi-dimensional Gaussian probability distribution.

    Instantiate with a list of pairs of floats (mean, variance)

    Public attributes:
      parameters -- the list used to instantiate the distribution

    """
    def __init__(self, parameters):
        self.parameters = parameters
        self.gaussian_params = [(mean, sqrt(variance))
                                for (mean, variance) in parameters]

    def get_sample(self):
        """Return a random sample from the distribution.

        Returns a list of pairs of floats

        """
        return [gauss(mean, stddev)
                for (mean, stddev) in self.gaussian_params]

    def __str__(self):
        s = " ".join("%5.2f +- %4.2f" % (mean, stddev)
                     for (mean, stddev) in self.parameters)
        return "<distribution %s>" % s


class Cem_optimiser(object):
    """Optimiser using the cross-entropy method.

    Usage:
       optimiser = Cem_optimiser(fitness_fn [, ...])
       optimiser.set_distribution(...)
       parameters = optimiser.run(...)

    Instantiate with a fitness function: FIXME.

    """
    def __init__(self, fitness_fn,
                 samples_per_generation=None,
                 elite_proportion=None,
                 step_size=None):
        self.fitness_fn = fitness_fn
        if samples_per_generation is None:
            samples_per_generation = 100
        if elite_proportion is None:
            elite_proportion = 0.1
        if step_size is None:
            step_size = 0.5
        self.samples_per_generation = samples_per_generation
        self.elite_proportion = elite_proportion
        self.step_size = step_size
        self.distribution = None
        self.dimension = None

    def set_distribution(self, distribution):
        """Set the current probability distribution."""
        self.distribution = distribution
        self.dimension = len(distribution.parameters)

    def find_elite_parameters(self):
        """Take samples and evaluate them, returning the elite ones.

        Returns a list of optimiser parameter vectors.

        """
        get_sample = self.distribution.get_sample
        sample_parameters = [get_sample()
                             for _ in xrange(self.samples_per_generation)]
        fitness_list = self.fitness_fn(sample_parameters)
        sorter = [(fitness, index)
                  for (index, fitness) in enumerate(fitness_list)]
        sorter.sort()
        elite_count = int(self.elite_proportion * self.samples_per_generation)
        return [sample_parameters[index]
                for (fitness, index) in sorter[-elite_count:]]

    def update_distribution(self, elites):
        """Update the current distribution based on the given elitss.

        elites -- list of optimiser parameter vectors

        """
        n = len(elites)
        new_distribution_parameters = []
        for i in range(self.dimension):
            v = [e[i] for e in elites]
            elite_mean = sum(v) / n
            elite_var = sum(map(square, v)) / n - square(elite_mean)
            old_mean, old_var = self.distribution.parameters[i]
            new_mean = (elite_mean * self.step_size +
                        old_mean * (1.0 - self.step_size))
            new_var = (elite_var * self.step_size +
                       old_var * (1.0 - self.step_size))
            new_distribution_parameters.append((new_mean, new_var))
        self.distribution = Distribution(new_distribution_parameters)

    def run_one_generation(self):
        """Run the optimiser for a single generation."""
        elite_parameters = self.find_elite_parameters()
        self.update_distribution(elite_parameters)

    def run(self, number_of_generations):
        """Run the optimiser for a specified number of generations.

        Returns the final probability distribution.

        """
        for i in xrange(number_of_generations):
            #print self.distribution
            self.run_one_generation()
        return self.distribution
