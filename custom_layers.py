from spektral.layers import GCNConv, GlobalSumPool,MessagePassing,GATConv,EdgeConv,GlobalAvgPool
import tensorflow.keras.layers as layers
from tensorflow.keras import initializers
import tensorflow as tf


class Conv_layer_relu(layers.Layer):
    def __init__(self,n_hidden,dropout=0.2):
        super(Conv_layer_relu,self).__init__()
        self.conv = GCNConv(n_hidden,
                            kernel_initializer=initializers.he_uniform(seed=None),
#                             kernel_regularizer="l1"
                           )
        self.norm = layers.BatchNormalization()        
        self.act  = layers.ReLU()         
        self.drop = layers.Dropout(dropout)
    def call(self, inputs):
        x,a = inputs
        x1 = self.conv([x,a])
        x1 = self.norm(x1)
        x1 = self.act(x1) 
        x1 = self.drop(x1)
        return x1
    
class MPConv_layer_relu(layers.Layer):
    def __init__(self,dropout=0.2):
        super(MPConv_layer_relu,self).__init__()
        self.conv = MessagePassing(aggregate="mean",kernel_initializer=initializers.he_uniform(seed=None),
#                                    kernel_regularizer="l1"
                                  )
        self.norm = layers.BatchNormalization()        
        self.act  = layers.ReLU()         
        self.drop = layers.Dropout(dropout)
    def call(self, inputs):
        x,a = inputs
        x1 = self.conv([x,a])
#         x1 = self.norm(x1)
#         x1 = self.act(x1) 
#         x1 = self.drop(x1)
        return x1
    
class GATConv_layer_relu(layers.Layer):
    def __init__(self,channels,dropout=0.2):
        super(GATConv_layer_relu,self).__init__()
        self.conv = GATConv(channels,
                            kernel_initializer=initializers.he_uniform(seed=None),
#                             kernel_regularizer="l1"
                           )
        self.norm = layers.BatchNormalization()        
        self.act = layers.ReLU()         
        self.drop = layers.Dropout(dropout)
    def call(self, inputs):
        x,a = inputs
        x1 = self.conv([x,a])
        x1 = self.norm(x1)
        x1 = self.act(x1) 
        x1 = self.drop(x1)
        return x1
    
    
class Dense_layer_relu(layers.Layer):
    def __init__(self,n_hidden,dropout=0.2):
        super(Dense_layer_relu,self).__init__()
        self.dense = layers.Dense(n_hidden,
                                  kernel_initializer=initializers.he_uniform(seed=None),
#                                   kernel_regularizer="l1"
                                 )
        self.norm = layers.BatchNormalization()        
        self.act  = layers.ReLU()         
        self.drop = layers.Dropout(dropout)
    
    def call(self, inputs):
        x1 = self.dense(inputs)
        x1 = self.norm(x1)
        x1 = self.act(x1) 
        x1 = self.drop(x1)
        return x1
    
class Dense_layer_tanh(layers.Layer):
    def __init__(self,n_hidden,dropout=0.2):
        super(Dense_layer_tanh,self).__init__()
        self.dense = layers.Dense(n_hidden,
                                  kernel_initializer=initializers.GlorotUniform(seed=None))
        self.norm = layers.BatchNormalization()        
        self.drop = layers.Dropout(dropout)
    
    def call(self, inputs):
        x1 = self.dense(inputs)
#         x1 = self.norm(x1)
        x1 = tf.keras.activations.tanh(x1)
#         x1 = self.drop(x1)
        return x1