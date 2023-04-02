import spektral.data as data
import tensorflow as tf
import numpy as np 
from tensorflow import keras
import os
import sys
import argparse
import math

from GAE.frams_interface.GraphDataset import GraphDataset
from GAE.architecture.autoencoder import EncoderGAE,EncoderVGAE, DecoderX, DecoderA, VGAE, GAE
from GAE.architecture.utils import *
from GAE.custom_layers import *
from GAE.architecture.base.LossManager import LossManager, LossTypes
from GAE.frams_interface.framasToGraph import FramsTransformer
from GAE.frams_interface.manager import gen_f0_from_tensors, FramsManager

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

def ensureDir(string):
    if os.path.isdir(string):
        return string
    else:
        raise NotADirectoryError(string)
                    
             
class AE_evolalg:
    def __init__(self,path_config,train_id) -> None:
        self.params_dict = load_config(path_config)

        self.frams_manager = FramsManager(self.params_dict['pathframs'])
        self.frams_transformer = FramsTransformer(self.params_dict['pathframs'],self.params_dict['adjsize'])
        ae_type=None
        if self.params_dict['variational'] == "True":
            self.variational=True
        else:
            self.variational=False

        if self.variational == True:
            ae_type="VGAE"
        else:
            ae_type="GAE"

        self.path_out = (str(self.params_dict['pathout'])+
                    str(self.params_dict['loss'])+
                    "/"+ae_type +
                    "/numfeatures"+str(self.params_dict['numfeatures']) +
                    "/adjsize"+str(self.params_dict['adjsize']) + 
                    "/batchsize"+str(self.params_dict['batchsize']) +
                    "/latentdim"+str(self.params_dict['latentdim'])+
                    "/nhidden"+str(self.params_dict['nhidden'])+
                    "/learningrate"+str(self.params_dict['learningrate'])+
                    "/convtype"+str(self.params_dict['convtype'])+
                    "/"
                    )
        self.model_name = ("model_enc_"+str(self.params_dict['convenc'])+"_"+str(self.params_dict['denseenc'])+
                    "_deca"+str(self.params_dict['densedeca'])+
                    "_decx"+str(self.params_dict['convdecx'])+"_"+str(self.params_dict['densedecx'])+
                    "_train_id_"+str(train_id)
                    )
                    
        if self.params_dict['loss'] is not LossTypes.No:
            lossManager = LossManager(self.params_dict['pathframs'],"eval-allcriteria_new.sim","vertpos")
            if self.params_dict['loss'] == LossTypes.joints:
                custom_loss = lossManager.joints_too_big_loss
            elif self.params_dict['loss'] == LossTypes.parts:
                custom_loss = lossManager.part_number_loss
            elif self.params_dict['loss'] == LossTypes.fitness:
                custom_loss = lossManager.fitness_comparison_loss
            elif self.params_dict['loss'] == LossTypes.dissim:
                custom_loss = lossManager.dissimilarity_comparison
            else:
                print(self.params_dict['loss']," is not supported, custom loss set to None")
                custom_loss = None
        else:
            custom_loss = None

        train, test = GraphDataset(self.params_dict['pathframs'], self.params_dict['pathdata'],size_of_adj=self.params_dict['adjsize'],max_examples=500).read()

        loader_train = data.BatchLoader(train, batch_size=self.params_dict['batchsize'])
        loader_test = data.BatchLoader(test, batch_size=self.params_dict['batchsize'])

        if self.variational == True:
            encoder = EncoderVGAE(latent_dim=self.params_dict['latentdim'],
                            n_hidden=self.params_dict['nhidden'],
                            num_conv=self.params_dict['convenc'],
                            num_dense=self.params_dict['denseenc'],
                            convtype=self.params_dict['convtype'])
        else:
            encoder = EncoderGAE(latent_dim=self.params_dict['latentdim'],
                        n_hidden=self.params_dict['nhidden'],
                        num_conv=self.params_dict['convenc'],
                        num_dense=self.params_dict['denseenc'],
                        convtype=self.params_dict['convtype'])
                            
        decoderA = DecoderA(adjency_size=self.params_dict['adjsize'],
                            latent_dim=self.params_dict['latentdim'],
                            num_dense=self.params_dict['densedeca'])
        decoderX = DecoderX(latent_dim=self.params_dict['latentdim'], 
                            adjency_size=self.params_dict['adjsize'],
                            num_features=self.params_dict['numfeatures'],
                            num_conv=self.params_dict['convdecx'],
                            num_dense=self.params_dict['densedecx'],
                            convtype=self.params_dict['convtype'])


        current_learning_rate = self.params_dict['learningrate']

        if self.variational == True:
            self.autoencoder = VGAE(encoder,decoderA,decoderX,custom_loss)
        else:
            self.autoencoder = GAE(encoder,decoderA,decoderX,custom_loss)

        self.opt = keras.optimizers.Adam(learning_rate=current_learning_rate)
        self.autoencoder.compile(optimizer=self.opt)

        (x,a),y = next(loader_train)
        _ = self.autoencoder.train_step([(tf.convert_to_tensor(x)),
                                            tf.convert_to_tensor(a),
                                            y])
        self.autoencoder.built = True

        if os.path.exists(self.path_out+self.model_name+"/"):
            print("Trying to load the model")
            _, _  = load_model(self.path_out,self.model_name,self.autoencoder)

        else:
            os.makedirs(self.path_out+self.model_name)

        self.path_save = self.path_out+self.model_name

    def prepareGenList(self,X,A,idx):
        gen_list = gen_f0_from_tensors(X,A)
        gen_correct = []
        idx_correct = []
        ec = self.frams_manager.frams.MessageCatcher.new()
        for g in range(len(gen_list)):
            gen = self.frams_manager.check_consistency_for_gen(gen_list[g])
            if gen is not None:
                gen = self.frams_manager.reduce_joint_length_for_gen(gen)
            if gen is not None:
                gen_correct.append(gen)
                idx_correct.append(idx[g])
        ec.close()
        return idx_correct,gen_correct

    def prepareXAforPopulation(self,population):
        x_all = []
        a_all = []
        for p in population:
            graph = self.frams_transformer.getGrafFromString(p) 
            x_all.append(graph.x)
            a_all.append(graph.a)
        return x_all,a_all

    def mutate_population(self,population,idx,m_range=[-0.33,0.33]):
        # translate to a and x
        print("new genotype")
        print(len(population))
        x,a = self.prepareXAforPopulation(population)
        if self.variational== True:
            z_mean, z_log_var, orginal_z  = self.autoencoder.encoder([(tf.convert_to_tensor(x)),
                                        tf.convert_to_tensor(a)])
        else:
            orginal_z  = self.autoencoder.encoder([(tf.convert_to_tensor(x)),
                                        tf.convert_to_tensor(a)])
        # mutate by adding random stuff to z 
        new_z_list = []
        for z in orginal_z.numpy():
            mutation  = np.random.uniform(m_range[0],m_range[1],self.params_dict['latentdim'])
            m_z = z + mutation
            new_z_list.append(m_z)
        new_z = tf.convert_to_tensor(new_z_list)
        recA = self.autoencoder.decoderA(new_z)
        recX = self.autoencoder.decoderX([new_z,recA])

        idx, geno = self.prepareGenList(recX,recA,idx)
        print(len(geno),len(idx))
        return idx, geno

    def train_autoencoder(self, training_population):

        train, test = GraphDataset(path_frames=self.params_dict['pathframs'],size_of_adj=self.params_dict['adjsize'],max_examples=500).convert(training_population)

        loader_train = data.BatchLoader(train, batch_size=self.params_dict['batchsize'])
        loader_test = data.BatchLoader(test, batch_size=self.params_dict['batchsize'])

        steps_train = math.ceil(train.n_graphs/self.params_dict['batchsize'])
        steps_test = math.ceil(test.n_graphs/self.params_dict['batchsize'])
        e = 0

        losses_all_train = []
        losses_all_test = []
        while True:
            if current_learning_rate > parsed_args.learningrate * pow(0.7,math.floor(e/40)):
                current_learning_rate = parsed_args.learningrate * pow(0.7,math.floor(e/40))
                self.opt.lr.assign(current_learning_rate)
            print("EPOCH",e)
            loss=None
            losses_all = []
            for _ in range(steps_train):        
                (x,a),y= next(loader_train)
                loss = self.autoencoder.train_step([tf.convert_to_tensor(x),
                                            tf.convert_to_tensor(a),
                                            y])
                losses_all.append([float(keras.backend.get_value(loss[l])) for l in loss])
                if tf.math.is_nan(loss['loss']):
                    print("LOSS == NAN")
                    break
                
            if tf.math.is_nan(loss['loss']):
                print("LOSS == NAN")
                break
            avg_losses_all = np.mean(losses_all,axis=0)
            np.set_printoptions(suppress=True, precision=3)
            print(avg_losses_all)
            losses_all_train.append(avg_losses_all)
            self.autoencoder.set_weights_for_loss(np.mean(losses_all_train[-5:],axis=0),e)
            
            test_loses = test_model(self.autoencoder,loader_test, steps_test, self.variational)
            losses_all_test.append(test_loses)
            if e%5 == 0:
                save_model(self.path_out, self.model_name, losses_all_train, losses_all_test, autoencoder, Variational=self.variational)
            print("Loss train: ",np.mean(avg_losses_all[0]))
            print("Loss test: ", np.mean(test_loses[0]))

def parseArguments():
    parser = argparse.ArgumentParser(
        description='Run this program with "python -u %s" if you want to disable buffering of its output.' % sys.argv[
            0])
    parser.add_argument('-pathconfig', type=str, required=True, help='Path to the Framsticks library without trailing slash.')
    return parser.parse_args()

if __name__ == "__main__":
    parsed_args = parseArguments()
    autoencoder = AE_evolalg(parsed_args.pathconfig)