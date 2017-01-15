import collections
import random


class MarkovNode(object):
    """ Node object referencing other nodes in the graph """


    def __init__(self):
        self.neighbors = collections.Counter()
        self.count = 0


    def increment(self, token):
        self.neighbors[token] += 1
        self.count += 1


    def decrement(self, token):
        if self.neighbors[token] <= 0:
            return
        self.neighbors[token] -= 1
        if not self.neighbors[token]:
            del self.neighbors[token]
        self.count -= 1


    def __len__(self):
        return self.count


    def get_random_key(self):
        if self.count <= 0:
            return None
        rand = random.randint(1, self.count)
        for key, amount in self.neighbors.items():
            rand -= amount
            if rand <= 0:
                return key


class MarkovGraph(object):
    """ Markov Chain represented by a graph """


    def __init__(self, level):
        self._root = MarkovNode()
        self._nodes = {}
        self._k = level


    def train(self, tokens):
        if self._k == 0:
            for token in tokens:
                self._root.increment(token)
        else:
            last_k = collections.deque(maxlen=self._k)
            for token in tokens:
                if len(last_k) == self._k:
                    key = tuple(last_k)
                    if key not in self._nodes:
                        self._nodes[key] = MarkovNode()
                    self._nodes[key].increment(token)
                    self._root.increment(key)
                last_k.append(token)


    def untrain(self, tokens):
        if self._k == 0:
            for token in tokens:
                self._root.decrement(token)
        else:
            last_k = collections.deque(maxlen=self._k)
            for token in tokens:
                if len(last_k) == self._k:
                    key = tuple(last_k)
                    if key in self._nodes:
                        self._nodes[key].decrement(token)
                        if not self._nodes[key]:
                            del self._nodes[key]
                        self._root.decrement(key)
                    else:
                        print("key '{}' not found".format(key), file=sys.stderr)
                last_k.append(token)


    def generate_tokens(self):
        if self._k == 0:
            key = self._root.get_random_key()
            if key is None:
                return
            yield key
        else:
            tokens = self._root.get_random_key()
            if tokens is None:
                return
            for token in tokens:
                yield token
            while tokens in self._nodes:
                next_tk = self._nodes[tokens].get_random_key()
                if next_tk is None:
                    return
                yield next_tk
                tokens = tokens[1:] + (next_tk,)


    def count(self):
        return self._root.count
