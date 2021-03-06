from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import numpy as np


class RandomAgent:
    def __init__(self, num_actions, *args, **kwargs):
        self.num_actions = num_actions

    def action(self, *args, **kwargs):
        return np.random.randint(self.num_actions)

    def update(self, *args, **kwargs):
        pass

    def linapprox(self, *args, **kwargs):
        return np.zeros(self.num_actions)

class TabularNStepQLearning:
    def __init__(self, state_shape, num_actions, n=1):
        self.num_actions = num_actions
        self.tab_shape = np.hstack([state_shape, num_actions])
        self.n = n

        self.min_eps = 0.1
        self.decay_len = 1 # 1e4
        self.alpha = 0.1 
        self.gamma = 0.99
        self.t = 0
        self.exp = []
        self.Qtable = np.zeros(self.tab_shape)

    @property
    def eps(self):
        _eps = 1 - self.t/self.decay_len
        return np.maximum(self.min_eps, _eps)

    def action(self, state):
        self.t += 1
        if np.random.uniform() > self.eps:
            a = np.argmax(self.Qtable[tuple(state)])
        else:
            a = np.random.randint(self.num_actions)
        return a

    def compute_G(self):
        """ Discounted reward"""
        G = 0
        for i in range(len(self.exp)):
            G = G + (self.gamma ** i) * self.exp[i][2]
        return G

    def update(self, s, a, r, s_, d, **kwargs):
        self.exp.append([s, a, r, s_])

        # Qmax = np.max(self.Qtable[tuple(s_)])
        # Q_as = self.Qtable[tuple(np.hstack([s, a]))]
        #
        # self.Qtable[tuple(np.hstack([s, a]))] = Q_as + self.alpha * (r + self.gamma * Qmax - Q_as)

        if d:  # Done --> loop through experience
            while len(self.exp) > 0:
                fs, fa, fr, fs_ = self.exp[0]
                G = self.compute_G()
                self.exp.pop(0)

                Q_fas = self.Qtable[tuple(np.hstack([fs, fa]))]
                self.Qtable[tuple(np.hstack([fs, fa]))] = Q_fas + self.alpha * (G - Q_fas)

        elif len(self.exp) < self.n:  # to early -- move along
            pass
        else:  # Normal n-step update w. bootstrapping
            fs, fa, fr, fs_ = self.exp[0]
            G = self.compute_G()
            G += (self.gamma ** self.n) * np.max(self.Qtable[tuple(s_)])
            self.exp.pop(0)

            Q_fas = self.Qtable[tuple(np.hstack([fs, fa]))]
            self.Qtable[tuple(np.hstack([fs, fa]))] = Q_fas + self.alpha * (G - Q_fas)


class TabularNStepSARSA(TabularNStepQLearning):
    def update(self, s, a, r, s_, a_, d, **kwargs):
        self.exp.append([s, a, r, s_, a_])
        
        if d:  # Done --> loop through experience
            while len(self.exp) > 0:
                fs, fa, fr, fs_, fa_ = self.exp[0]
                G = self.compute_G()
                self.exp.pop(0)
                
                Q_fas = self.Qtable[tuple(np.hstack([fs, fa]))]
                self.Qtable[tuple(np.hstack([fs, fa]))] = Q_fas + self.alpha * (G - Q_fas)
            
        elif len(self.exp) < self.n:  # to early -- move along
            pass
        else:  # Normal n-step update w. bootstrapping
            fs, fa, fr, fs_, fa_ = self.exp[0]
            G = self.compute_G()
            G += (self.gamma**self.n) * self.Qtable[tuple(np.hstack([s_, a_]))]
            self.exp.pop(0)

            Q_fas = self.Qtable[tuple(np.hstack([fs, fa]))]
            self.Qtable[tuple(np.hstack([fs, fa]))] = Q_fas + self.alpha * (G - Q_fas)


class ApproximateNStepSARSA:
    def __init__(self, state_shape, num_actions, n=1, alpha=0.01):
        self.num_actions = num_actions
        self.w = np.zeros(np.hstack([np.prod(state_shape), num_actions]))
        self.n = n

        self.min_eps = 0.1
        self.decay_len = 1  # 1e4
        self.alpha = alpha / n  # alpha 0.01 seem to work for n=8 and n=1, not n=20.
        self.gamma = 0.99
        self.t = 0
        self.exp = []

    @property
    def eps(self):
        _eps = 1 - self.t/self.decay_len
        return np.maximum(self.min_eps, _eps)
    
    def linapprox(self, s, a=None):
        qsa = self.w.T.dot(s)
        
        if a is not None:
            qsa = qsa[a]
        return qsa

    def action(self, state):
        self.t += 1
        if np.random.uniform() > self.eps:
            a = np.argmax(self.linapprox(state))
        else:
            a = np.random.randint(self.num_actions)
        return a

    def compute_G(self):
        """ Discounted reward"""
        G = 0
        for i in range(len(self.exp)):
            G = G + (self.gamma ** i) * self.exp[i][2]
        return G

    def update(self, s, a, r, s_, a_, d, **kwargs):
        self.exp.append([s, a, r, s_, a_])
        
        if d:  # Done --> loop through experience
            while len(self.exp) > 0:
                fs, fa, fr, fs_, fa_ = self.exp[0]
                G = self.compute_G()
                self.exp.pop(0)
                
                qsa = self.linapprox(fs,fa)
                self.w[:,fa] += self.alpha * (G - qsa) * fs 
                
        elif len(self.exp) < self.n:  # to early -- move along
            pass
        else:  # Normal n-step update w. bootstrapping
            fs, fa, fr, fs_, fa_ = self.exp[0]
            G = self.compute_G()
            qsa = self.linapprox(s_,a_)
            G += (self.gamma**self.n) * qsa
            self.exp.pop(0)

            qsa = self.linapprox(fs,fa)
            self.w[:,fa] += self.alpha * (G - qsa) * fs


# True SARSA
class TrueOnlineLambdaSARSA:
    def __init__(self, state_shape, num_actions):
        self.num_actions = num_actions
        self.w = np.zeros(np.hstack([np.prod(state_shape), num_actions]))
        self.z = np.zeros(self.w.shape)

        self.min_eps = 0.1
        self.decay_len = 1 # 1e4
        self.alpha = 0.05
        self.gamma = 1

        self.lambd = 0
        self.Q_old = 0

        self.t = 0
        self.exp = []
        #TODO x(terminal,a) = 0, so make sure that's the case
        
    @property
    def eps(self):
        _eps = 1 - self.t/self.decay_len
        return np.maximum(self.min_eps, _eps)
    
    def linapprox(self, s, a=None):
        qsa = self.w.T.dot(s)
        if(not a==None):
            qsa = qsa[a]
        return qsa

    def action(self, state):
        self.t += 1
        if np.random.uniform() > self.eps:
            a = np.argmax(self.linapprox(state))
        else:
            a = np.random.randint(self.num_actions)
        return a

    def compute_G(self): #TOO: is this method needed?
        """ Discounted reward"""
        G = 0
        for i in range(len(self.exp)):
            G = G + (self.gamma ** i) * self.exp[i][2]
        return G

    def reset(self): 
        self.z = np.zeros(self.w.shape)
        self.Q_old = 0
        return #TODO: if we use this, place it in run_loop
    
    def update(self, s, a, r, s_, a_, d, **kwargs):
        self.exp.append([s, a, r, s_, a_])
        
        if d:
            s = np.zeros_like(s)
            
        Q = self.linapprox(s,a)
        Q_prime = self.linapprox(s_,a_)
        
        delta = r + self.gamma*Q_prime - Q
        self.z[:,a] = self.gamma*self.lambd*self.z[:,a] + (1 - self.alpha*self.gamma*self.lambd*self.z[:,a].T.dot(s))*s
        self.w[:,a] = self.w[:,a] + self.alpha*(delta + Q - self.Q_old)*self.z[:,a] - self.alpha*(Q - self.Q_old)*s
        self.Q_old = Q
        
        return 
       
# TB lambda
