0#With Proj units as input 
"""
This tutorial introduces the multilayer perceptron using Theano.

 A multilayer perceptron is a logistic regressor where
instead of feeding the input to the logistic regression you insert a
intermediate layer, called the hidden layer, that has a nonlinear
activation function (usually tanh or sigmoid) . One can use many such
hidden layers making the architecture deep. The tutorial will also tackle
the problem of MNIST digit classification.

.. math::

    f(x) = G( b^{(2)} + W^{(2)}( s( b^{(1)} + W^{(1)} x))),

References:

    - textbooks: "Pattern Recognition and Machine Learning" -
                 Christopher M. Bishop, section 5

"""
__docformat__ = 'restructedtext en'


import cPickle
import gzip
import os
import sys
import time

import numpy
import scipy.io
import gc
import theano
import theano.tensor as T
from numpy import * 
from theano import sparse as Tsparse 
import scipy.sparse as sp 
from logistic_sgd7 import LogisticRegression
from NNLMio import write_params_matlab

copy_size=50000

class ProjectionLayer_ngram(object):
    def __init__(self, rng, input, nhistory, feature,n_feat, n_in, n_out, N=4096, W=None,
                 sparse=None,activation=None):

        self.input = input
        if W is None:
            W_values = numpy.asarray(rng.uniform(
                    low=-numpy.sqrt(6. / (N*n_in + n_out)),
                    high=numpy.sqrt(6. / (N*n_in + n_out)),
                    size=(N*n_in, n_out)), dtype=theano.config.floatX)
            if activation == theano.tensor.nnet.sigmoid:
                W_values *= 4

            W = theano.shared(value=W_values, name='W', borrow=True)
        else:
            w_values=W
            W = theano.shared(value=w_values, name='W',borrow=True)
	#self.inp = numpy.zeros(input.ndim)
	#self.inp[T.arange(input.shape[0]), input ] =1

        self.W = W
        lin_output = T.dot(self.input, self.W)
        for history in nhistory:
            lin_output = T.concatenate((lin_output,T.dot(history,self.W)),axis=1)
         
        if n_feat==0:
            self.output = lin_output
        else:
            self.output = T.concatenate((lin_output,feature),axis=1)
        # parameters of the model
        self.params = [self.W]


class HiddenLayer(object):
    def __init__(self, rng, input, n_in, n_out, W=None, b=None,
                 activation=T.tanh):

        self.input = input

        if W is None:
            W_values = numpy.asarray(rng.uniform(
                    low=-numpy.sqrt(6. / (n_in + n_out)),
                    high=numpy.sqrt(6. / (n_in + n_out)),
                    size=(n_in, n_out)), dtype=theano.config.floatX)
            if activation == theano.tensor.nnet.sigmoid:
                W_valueds *= 4

            W = theano.shared(value=W_values, name='W', borrow=True)
        else:
            W = theano.shared(value=W,name='W',borrow=True)

        if b is None:
            b_values = numpy.zeros((n_out,), dtype=theano.config.floatX)
            b = theano.shared(value=b_values, name='b', borrow=True)
        else:
            b = theano.shared(value=b, name='b', borrow=True)
        self.W = W
        self.b = b

        lin_output = T.dot(input, self.W) + self.b
        self.output = (lin_output if activation is None
                       else activation(lin_output))
        # parameters of the model
        self.params = [self.W, self.b]


class MLP(object):
    """Multi-Layer Perceptron Class

    A multilayer perceptron is a feedforward artificial neural network model
    that has one layer or more of hidden units and nonlinear activation
    """
    
    def __init__(self, rng, input, nhistory, feature,n_features, n_in,n_P, n_hidden, n_out, ngram=3, Voc=4096,pW=None,hW=None,hB=None,lW=None,lB=None,lW2=None,lB2=None):
        
        self.projectionLayer = ProjectionLayer_ngram(rng=rng, input=input, nhistory=nhistory, feature=feature, n_feat = n_features, n_in=1, n_out=n_P, W=pW, N=Voc,activation=None)
        self.hiddenLayer = HiddenLayer(rng=rng, input=self.projectionLayer.output,
                                       n_in=n_P*(ngram-1)+n_features, n_out=n_hidden,
                                       activation=T.tanh,W=hW,b=hB)
        # The logistic regression layer gets as input the hidden units++++++++++++++++++++
        # of the hidden layer

        self.logRegressionLayer = LogisticRegression(input=self.hiddenLayer.output,
                                                     n_in=n_hidden,
                                                     n_out=n_out,W=lW,b=lB,W2=lW2,b2=lB2)

        # L1 norm ; one regularization option is to enforce L1 norm to
        # be small
        self.L1 = abs(self.hiddenLayer.W).sum() \
                + abs(self.logRegressionLayer.W).sum() \
                + abs(self.logRegressionLayer.W2).sum()


        # square of L2 norm ; one regularization option is to enforce
        # square of L2 norm to be small
        self.L2_sqr = (self.hiddenLayer.W ** 2).sum() \
                    + (self.logRegressionLayer.W ** 2).sum() \
                    + (self.logRegressionLayer.W ** 2).sum()


        # negative log likelihood of the MLP is given by the negative
        # log likelihood of the output of the model, computed in the
        # logistic regression layer
        self.negative_log_likelihood = self.logRegressionLayer.negative_log_likelihood
        # same holds for the function computing the number of errors

        self.tot_ppl = self.logRegressionLayer.tot_ppl

        # the parameters of the model are the parameters of the two layer it is
        # made out o
        
        self.params = self.projectionLayer.params + self.hiddenLayer.params + self.logRegressionLayer.params  
        
    def get_params_pW(self):
        return (self.projectionLayer.W)
    def get_params_hW(self):
        return self.hiddenLayer.W
    def get_params_hb(self):
        return self.hiddenLayer.b
    def get_params_lW(self):
        return self.logRegressionLayer.W 
    def get_params_lb(self):
        return self.logRegressionLayer.b
    def get_params_lW2(self):
        return self.logRegressionLayer.W2
    def get_params_lb2(self):
        return self.logRegressionLayer.b2

def convert_to_sparse(x,N=4096):
    data=[]
    for i in x:
        y = zeros((N),dtype=theano.config.floatX)
        if i >=N:
            i=2
        y[i]=1
        z=y
        data.append(z)
    return data 

def convert_to_sparse_combine(Listx,N=4096,a=0,b=1e20):
    data=[]
    b = min(b,len(Listx[0]))

    for n in range(a,b):
        y = zeros((N),dtype=theano.config.floatX)
        for x in Listx:
            i = x[n]
            if i >=N:
                i=2
            y[i]=1
        z=y
        data.append(z)
    return data

def shared_data(data,type="float",sparse=False,borrow=False):
    data_x = data
    if sparse==False:
        shared_x = theano.shared(numpy.asarray(data_x,dtype=theano.config.floatX),
                                 borrow=borrow)
    else:
        shared_x = theano.shared(data_x,
                                 borrow=borrow)

    if type=="float":
        return shared_x 
    elif type=="int"or type=="int32":
        return T.cast(shared_x, 'int32')

def GetPenaltyVector(y,penalty,Wids):
    # Wids = list of words that need to be penalized with penalty
    vec_penalty  = zeros(len(y ))
    i  = 0
    count = 0
    while i < len(vec_penalty):
        if y[i] in Wids: 
            vec_penalty[i]=penalty
	    count = count + 1
        else:
            vec_penalty[i]=1
        i=i+1
        
        vec_penalty_shared  =  theano.shared(numpy.asarray(vec_penalty,
                                                           dtype=theano.config.floatX),
                             borrow=True)
    print >> sys.stderr, "Penalized ",count," words", "with penalty", penalty 
    return vec_penalty_shared


def train_mlp(NNLMdata,NNLMFeatData,OldParams,ngram,n_feats,n_unk,N,P,H,learning_rate, L1_reg, L2_reg, n_epochs,batch_size,adaptive_learning_rate,fparam):
            
    learning_rate0 = learning_rate
    if n_unk > 0:
	rev_n_unk  = 1./n_unk 
    else:
	rev_n_unk  = 1
    UNKw = []
    #Read ngram training examples and corresponding y labels 
    ntrain_set_x = NNLMdata[0][0]
    ntrain_set_y = NNLMdata[0][1]
        
    nvalid_set_x = NNLMdata[1][0]
    nvalid_set_y = NNLMdata[1][1]
    
    ntest_set_x =  NNLMdata[2][0]
    ntest_set_y =  NNLMdata[2][1]
    
    #Convert valid and test set to sparse and shared objects 
    valid_set_x_sparse=[]
    for valid_set_xi in nvalid_set_x:
        shared_x = shared_data(convert_to_sparse(valid_set_xi,N))
        valid_set_x_sparse.append(shared_x) 

    test_set_x_sparse=[]
    for test_set_xi in ntest_set_x:
        shared_x = shared_data(convert_to_sparse(test_set_xi,N))
        test_set_x_sparse.append(shared_x) 

    valid_set_y  = shared_data(nvalid_set_y,"int")
    test_set_y   = shared_data(ntest_set_y,"int")

    if n_feats > 0:
        ntrain_set_featx = NNLMFeatData[0][0]
        ntrain_set_featy = NNLMFeatData[0][1]

        nvalid_set_featx = NNLMFeatData[1][0]
        nvalid_set_featy =  NNLMFeatData[1][1]

        ntest_set_featx =  NNLMFeatData[2][0]
        ntest_set_featy =  NNLMFeatData[2][1]

        vald_set_featx_sparse  = shared_data(convert_to_sparse_combine(nvalid_set_featx,n_feats))
            
        test_set_featx_sparse  = shared_data(convert_to_sparse_combine(ntest_set_featx,n_feats))

        valid_set_featy  = shared_data(nvalid_set_featy,"int")
        test_set_featy   = shared_data(ntest_set_featy,"int")
        
    #UNKw.append(2)
    if n_unk > 0:
        valid_error_penalty = GetPenaltyVector(nvalid_set_y,rev_n_unk,UNKw)
        test_error_penalty  = GetPenaltyVector(ntest_set_y,rev_n_unk,UNKw)
            
    ######################
    # BUILD ACTUAL MODEL # 
    ######################
    print >> sys.stderr, '... building the model'

    # allocate symbolic variables for the data
    index = T.lscalar()    # index to a [mini]batch
    x1 = T.matrix('x1')  # the data is presented as rasterized images
    x2 = T.matrix('x2')
    x3 = T.matrix('x3')
    x4 = T.matrix('x4')
    x5 = T.matrix('x5')
    x6 = T.matrix('x6')
    xfeat = T.matrix('xfeat') # if we hav features 
    y = T.ivector('y')  # the labels are presented as 1D vector of
    error_penalty = T.fvector('error_penalty') # In case some word are more important than others, we give them additional penalty. Leave as [] for uniform penalty
    
    rng = numpy.random.RandomState(1234)
    # construct the MLP class
    if OldParams:
        pW,hW,hB,lB,lB2,lW,lW2 = OldParams
    else:
        pW = hW = hB = lB = lB2 = lW = lW2 = None
    if ngram==2:
        classifier = MLP(rng=rng, input=x1, nhistory = [] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)
    elif ngram==3:
        classifier = MLP(rng=rng, input=x1, nhistory = [x2] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)
    elif ngram==4:
        classifier = MLP(rng=rng, input=x1, nhistory = [x2,x3] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)
    elif ngram==5:
        classifier = MLP(rng=rng, input=x1, nhistory = [x2,x3,x4] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)
    elif ngram==6:
        classifier = MLP(rng=rng, input=x1, nhistory = [x2,x3,x4,x5] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)
    elif ngram==7:
        classifier = MLP(rng=rng, input=x1, nhistory = [x2,x3,x4,x5,x6] ,feature=xfeat,n_features=n_feats,n_in=1, n_P=P, n_hidden=H, n_out=N, Voc=N,ngram=ngram,pW=pW,hW=hW,hB=hB,lW=lW,lW2=lW2,lB=lB,lB2=lB2)

    # the cost we minimize during training is the negative log likelihood of
    # the model plus the regularization terms (L1 and L2); cost is expressed
    # here symbolically
    if n_unk > 0:
        cost = classifier.negative_log_likelihood(y,error_penalty) \
            + L1_reg * classifier.L1 \
            + L2_reg * classifier.L2_sqr
    else:
        cost = classifier.negative_log_likelihood(y) \
            + L1_reg * classifier.L1 \
            + L2_reg * classifier.L2_sqr

    # compiling a Theano function that computes the mistakes that are made
    # by the model on a minibatch
    print >> sys.stderr, "ngram:", ngram
    
    Tgivens = {}
    Tgivens[x1]= test_set_x_sparse[0][index * batch_size:(index + 1) * batch_size]
    if ngram>=3:
        Tgivens[x2] =  test_set_x_sparse[1][index * batch_size:(index + 1) * batch_size]
    if ngram>=4:
        Tgivens[x3] =  test_set_x_sparse[2][index * batch_size:(index + 1) * batch_size]
    if ngram>=5:
        Tgivens[x4] =  test_set_x_sparse[3][index * batch_size:(index + 1) * batch_size]
    if ngram>=6:
        Tgivens[x5] =  test_set_x_sparse[4][index * batch_size:(index + 1) * batch_size]
    if ngram>=7:
        Tgivens[x6] =  test_set_x_sparse[5][index * batch_size:(index + 1) * batch_size]
    if n_feats>0:
        Tgivens[xfeat] = test_set_featx_sparse[index * batch_size:(index + 1) * batch_size]

    if n_unk > 0:
        Tgivens[error_penalty] = test_error_penalty[index * batch_size:(index + 1) * batch_size]
        Touts = classifier.tot_ppl(y,error_penalty)
    else:
        Touts = classifier.tot_ppl(y)

    Tgivens[y] = test_set_y[index * batch_size:(index + 1) * batch_size]

        
    test_model = theano.function(inputs=[index],
                                 outputs= Touts,
                                 on_unused_input='warn',
                                 givens= Tgivens )

    validate_model = theano.function(inputs=[index],
                                     outputs=Touts, 
                                     on_unused_input='warn',
                                     givens= Tgivens ) 

    final_weights = theano.function(inputs=[], outputs=[classifier.get_params_pW(),classifier.get_params_hW(),classifier.get_params_hb(),
                                                        classifier.get_params_lW(),classifier.get_params_lb(),classifier.get_params_lW2(),classifier.get_params_lb2()])

    # Get counts etc... 
    tot_train_size = len(ntrain_set_y)    
    n_train_parts = tot_train_size/(copy_size) +  int( tot_train_size%copy_size!=0)
    n_train_batches = copy_size/batch_size
    batch_size_train = batch_size
    n_valid_batches = len(nvalid_set_y) / batch_size
    n_test_batches = len(ntest_set_y)/ batch_size   

    # compute the gradient of cost with respect to theta (sotred in params)
    # the resulting gradients will be stored in a list gparams
    gparams = []
    for param in classifier.params:
        gparam = T.grad(cost, param)
        gparams.append(gparam)
        
    # specify how to update the parameters of the model as a dictionary
    updates = {}
    for param, gparam in zip(classifier.params, gparams):
        updates[param] = param - learning_rate * gparam

    print >> sys.stderr, '... training'

    # early-stopping parameters
    patience = 100000  # look as this many examples regardless
    patience_increase = 10  # wait this much longer when a new best is
                           # found
    improvement_threshold = 0.998  # a relative improvement of this much is
                                   # considered significant
    epsilon = (1-improvement_threshold) *0.05; #parameter for adaptive learning rate 
    validation_frequency = min(n_train_batches, patience / 2)
                                  # go through this many
                                  # minibatche before checking the network
                                  # on the validation set; in this case we
                                  # check every epoch
    # Initialize training 
    best_params = None
    best_validation_loss = numpy.inf
    best_iter = 0.
    test_score = 0.
    start_time = time.clock()
    epoch = 0
    done_looping = False    
    
    print >> sys.stderr, "Training parts:", n_train_parts,",Copy size:",copy_size,",Total training size:",tot_train_size
    pW,hW,hB,lW,lB,lW2,lB2 = final_weights() 

    #share training y , training features 
    train_set_y = shared_data(ntrain_set_y,"int")
    if n_feats>0:
        train_set_featx_sparse  = shared_data(convert_to_sparse_combine(ntrain_set_featx,n_feats))

    #convert training data to numpy arrays.
    train_set_x_sparse_notshared = [] 
    for train_set_xi in ntrain_set_x:
        train_x = convert_to_sparse(train_set_xi,N)
        train_set_x_sparse_notshared.append(numpy.asarray(train_x,dtype=theano.config.floatX))

    while (epoch < n_epochs) and (not done_looping):
        epoch = epoch + 1
        totcost=0
	updates = {}
	for param, gparam in zip(classifier.params, gparams):
            updates[param] = param - learning_rate * gparam

        print >> sys.stderr, "Current learning rate:", learning_rate
        for parts_index in range(n_train_parts):

            #convert training integers  1-of-N vectors into shared objects 
            train_set_x_sparse=[]
            for train_set_xi in train_set_x_sparse_notshared:
                shared_x = theano.shared( train_set_xi[parts_index * copy_size:min(tot_train_size,(parts_index + 1) * copy_size)],
                                          borrow=False )
                train_set_x_sparse.append(shared_x)
           
            Tgivens = {}
            Tgivens[x1] = train_set_x_sparse[0][index * batch_size:(index + 1) * batch_size]
            if ngram>=3:
                Tgivens[x2] =  train_set_x_sparse[1][index * batch_size:(index + 1) * batch_size]
            if ngram>=4:
                Tgivens[x3] =  train_set_x_sparse[2][index * batch_size:(index + 1) * batch_size]
            if ngram>=5:
                Tgivens[x4] =  train_set_x_sparse[3][index * batch_size:(index + 1) * batch_size]
            if ngram>=6:
                Tgivens[x5] =  train_set_x_sparse[4][index * batch_size:(index + 1) * batch_size]
            if ngram>=7:
                Tgivens[x6] =  train_set_x_sparse[5][index * batch_size:(index + 1) * batch_size]
            if n_feats>0:
                Tgivens[xfeat] = train_set_featx_sparse[parts_index * copy_size + index * batch_size:parts_index * copy_size + (index + 1) * batch_size]

            Tgivens[y] = train_set_y[parts_index * copy_size +  index * batch_size:parts_index * copy_size +  (index + 1) * batch_size]

            if n_unk > 0:
                train_error_penalty = GetPenaltyVector(ntrain_set_y[parts_index * copy_size:min(tot_train_size, (parts_index+ 1) * copy_size)],rev_n_unk,UNKw)
                Tgivens[error_penalty] = train_error_penalty[index * batch_size:(index + 1) * batch_size]

            train_model = theano.function(inputs=[index], outputs=cost,                                                                      
                                          updates=updates,                     
                                          givens= Tgivens)
            
            n_train_batches = len(ntrain_set_y[parts_index * copy_size:min(tot_train_size, (parts_index+ 1) * copy_size)])/batch_size
           
            print >> sys.stderr, "Training part:", parts_index 
            for minibatch_index in xrange(n_train_batches):
		validation_frequency = min(n_train_batches, patience / 2)
                if minibatch_index * batch_size > len(ntrain_set_y):
                    break
                minibatch_avg_cost = train_model(minibatch_index)
                totcost+=minibatch_avg_cost
                
                iter = epoch * n_train_batches + minibatch_index
                
                if (iter + 1) % validation_frequency == 0:
                    # compute zero-one loss on validation set
                    validation_losses = [validate_model(i) for i
                                         in xrange(n_valid_batches)]
                    this_validation_loss = numpy.power(10, numpy.mean(validation_losses))
                    
                    print >> sys.stderr, ('epoch %i, minibatch %i/%i, validation error %f %%' %
                          (epoch, minibatch_index + 1, n_train_batches,
                           this_validation_loss))

                    # if we got the best validation score until now
                    if this_validation_loss < best_validation_loss:
                    #improve patience if loss improvement is good enough
			done_looping= False;
                        if this_validation_loss < best_validation_loss *  \
                                improvement_threshold:
                            patience = max(patience, iter * patience_increase)

                        best_validation_loss = this_validation_loss
                        best_iter = iter

                        # test it on the test set
                        test_losses = [test_model(i) for i
                                       in xrange(n_test_batches)]
                        test_score = numpy.power(10, numpy.mean(test_losses))
			pW,hW,hB,lW,lB,lW2,lB2 = final_weights()

                        print >> sys.stderr, (('     epoch %i, minibatch %i/%i, test error of '
                               'best model %f %%') %
                              (epoch, minibatch_index + 1, n_train_batches,
                               test_score))

            gc.collect()
            del train_set_x_sparse
            
        if adaptive_learning_rate:
	    if learning_rate > 0.004:
	        learning_rate = float(learning_rate0)/(1 + float(iter*epsilon))
            else:
		learning_rate = 0.005
	
        fl = 'stoppage'
        stop=0
        for sl in open(fl,'r'):
            if sl.strip()=="STOP":
                stop=1
        if stop==1:
            break
        if patience <= iter:
            done_looping = True
            print >> sys.stderr,  "done looping","patience:",patience,"iter:",iter   
	    break
        print >> sys.stderr, "Total Cost in traning:", totcost
    
    end_time = time.clock()
    print >> sys.stderr, (('Optimization complete. Best validation score of %f %% '
           'obtained at iteration %i, with test performance %f %%') %
          (best_validation_loss, best_iter, test_score ))
    print >> sys.stderr, ('The code for file ' +
                          os.path.split(__file__)[1] +
                          ' ran for %.2fm' % ((end_time - start_time) / 60.))
    
    write_params_matlab(fparam,pW,hW,hB,lB,lB2,lW,lW2)


        
if __name__ == '__main__':
    test_mlp()
