import graph
import pickle


class TokenizationStrategy:
    @classmethod
    def tokenize(self, data):
        raise NotImplementedError
        yield None


class CharacterStrategy(TokenizationStrategy):
    @classmethod
    def tokenize(self, data):
        yield from data


class WordStrategy(TokenizationStrategy):
    @classmethod
    def tokenize(self, data):
        yield from data.split()


class RandomWriter(object):
    """A Markov chain based random data generator."""


    class_version = 1.1
    def __init__(self, level, strategy):
        self.version = self.__class__.class_version
        self._level = level
        self._strategy = strategy
        self._graph = graph.MarkovGraph(level)
        self.trained = False


    def generate_tokens(self):
        """Generate tokens using the model."""
        if not self.trained:
            return
        yield from self._graph.generate_tokens()


    @classmethod
    def unpickle(cls, pickle_bytes):
        rw = pickle.loads(pickle_bytes)
        if not hasattr(rw, 'version'):
            rw.version = 0.0
        if rw.version < rw.class_version:
            rw.upgrade()
        return rw


    def upgrade(self):
        if self.version < 1.0:
            self.version = 1.0
            if hasattr(self, 'tokenization'):
                del self.tokenization
        if self.version < 1.1:
            self.version = 1.1
            self.trained = self._graph.count() > 0


    def train(self, data):
        """Compute the probabilities based on the data given."""
        if not isinstance(data, str):
            raise TypeError("Training expects string data!")
        self._graph.train(self._strategy.tokenize(data))
        self.trained = self._graph.count() > 0


    def untrain(self, data):
        """Remove instances of trained data from graph"""
        if not isinstance(data, str):
            raise TypeError("Training expects string data!")
        self._graph.untrain(self._strategy.tokenize(data))
        self.trained = self._graph.count() > 0
