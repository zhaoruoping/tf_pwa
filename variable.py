import tensorflow as tf

def fix_value(x):
  def f(shape=None,dtype=None):
    if dtype is not None:
      return tf.Variable(x,dtype=dtype)
    return x
  return f

def rand_value(x):
  def f(shape=None,dtype=None):
    if dtype is not None:
      return tf.Variable(x*tf.random.uniform((),dtype=dtype),dtype=dtype)
    return x*tf.random.uniform((),dtype=dtype)
  return f

class Vars(object):
  def __init__(self, env):
    self.env = env
    self.variables = {}

  def add(self,name,size=None,var=None,trainable=True,**args):
    if name not in self.variables:
      if var is None:
        if size is None:
          self.variables[name] = self.env.add_weight(name,trainable=trainable,**args)
        else:
          self.variables[name] = self.env.add_weight(name,initializer=rand_value(size),trainable=trainable,**args)
      else:
        self.variables[name] = self.env.add_weight(name,initializer=fix_value(var),trainable=trainable,**args)
    return self.variables[name]
  
  __call__ = add
  
  def get(self,name):
    if name not in self.variable:
      raise "%s not found"%name
    return self.variables[name]