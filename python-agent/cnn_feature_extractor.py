# -*- coding: utf-8 -*-
from __future__ import print_function
import sys

import numpy as np
import chainer
from chainer import cuda
import chainer.functions as F
from chainer.links import caffe


class CnnFeatureExtractor:
    def __init__(self, gpu, model, model_type, out_dim):
        self.gpu = gpu
        self.model = 'bvlc_alexnet.caffemodel'
        self.model_type = 'alexnet'
        self.batchsize = 1
        self.out_dim = out_dim

        if self.gpu >= 0:
            cuda.check_cuda_available()
        
        print('Loading Caffe model file %s...' % self.model, file = sys.stderr)
        self.func = caffe.CaffeFunction(self.model)
        print('Loaded', file=sys.stderr)
        if self.gpu >= 0:
            cuda.get_device(self.gpu).use()
            self.func.to_gpu(self.gpu)

        if self.model_type == 'alexnet':
            self.in_size = 227
            mean_image = np.load('ilsvrc_2012_mean.npy')
            del self.func.layers[15:23]
            self.outname = 'pool5'
            #del self.func.layers[13:23]
            #self.outname = 'conv5'

        cropwidth = 256 - self.in_size
        start = cropwidth // 2
        stop = start + self.in_size
        self.mean_image = mean_image[:, start:stop, start:stop].copy()
                
    def call_external_model(self, x):
        '''
        This method return value after converting with relu function.
        Therefore the value is [0,] in each element 
        '''
        y = self.func(inputs={'data': x}, outputs=[self.outname], train=False)[0]
        return y

    def feature(self, camera_image):
        x_batch = np.ndarray((self.batchsize, 3, self.in_size, self.in_size), dtype=np.float32)
        image = np.asarray(camera_image).transpose(2, 0, 1)[::-1].astype(np.float32)
        image -= self.mean_image

        x_batch[0] = image
        xp = cuda.cupy if self.gpu >= 0 else np
        x_data = xp.asarray(x_batch)

        if self.gpu >= 0:
            x_data=cuda.to_gpu(x_data, device=self.gpu)
        
        x = chainer.Variable(x_data, volatile=True)
        mat = self.call_external_model(x)

        if self.gpu >= 0:
            mat = cuda.to_cpu(mat.data, device=self.gpu)
            mat = mat.reshape(self.out_dim)
        else:
            mat = mat.data.reshape(self.out_dim)

        return mat
        
    def __call__(self, x):
        return self.feature(x)