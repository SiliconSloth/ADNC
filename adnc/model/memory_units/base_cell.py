# Copyright 2018 Jörg Franke
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
from abc import abstractmethod, ABCMeta
import numpy as np
import tensorflow as tf


class BaseMemoryUnitCell():
    def __init__(self, input_size, memory_length, memory_width, read_heads, bypass_dropout=False, dnc_norm=False,
                 seed=100, reuse=False, analyse=False, dtype=tf.float32, name='base'):

        self.rng = np.random.RandomState(seed=seed)
        self.seed = seed
        self.dtype = dtype
        self.analyse = analyse

        # dnc parameters
        self.input_size = input_size
        self.h_N = memory_length
        self.h_W = memory_width
        self.h_RH = read_heads

        self.dnc_norm = dnc_norm
        self.bypass_dropout = bypass_dropout

        self.reuse = reuse
        self.name = name

    @property
    @abstractmethod
    def state_size(self):
        pass

    @abstractmethod
    def zero_state(self):
        pass

    @property
    def output_size(self):
        return self.h_RH * self.h_W + self.input_size

    @property
    def trainable_variables(self):
        return tf.get_collection('memory_unit')

    @property
    def parameter_amount(self):
        var_list = self.trainable_variables
        parameters = 0
        for variable in var_list:
            shape = variable.get_shape()
            variable_parametes = 1
            for dim in shape:
                variable_parametes *= dim.value
            parameters += variable_parametes
        return parameters

    @staticmethod
    def _calculate_content_weightings(memory, keys, strengths):

        similarity_numerator = tf.matmul(keys, memory, adjoint_b=True)

        norm_memory = tf.sqrt(tf.reduce_sum(tf.square(memory), axis=2, keepdims=True))
        norm_keys = tf.sqrt(tf.reduce_sum(tf.square(keys), axis=2, keepdims=True))
        similarity_denominator = tf.matmul(norm_keys, norm_memory, adjoint_b=True)

        similarity = similarity_numerator / similarity_denominator
        similarity = tf.squeeze(similarity)
        adjusted_similarity = similarity * strengths

        softmax_similarity = tf.nn.softmax(adjusted_similarity, dim=-1)

        return softmax_similarity

    @staticmethod
    def _read_memory(memory, read_weightings):
        read_vectors = tf.matmul(read_weightings, memory)
        return read_vectors