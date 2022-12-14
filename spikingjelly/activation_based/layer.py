import logging

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from . import base, functional
from torch import Tensor
from torch.nn.common_types import _size_any_t, _size_1_t, _size_2_t, _size_3_t
from typing import Optional, List, Tuple, Union
from typing import Callable
from torch.nn.modules.batchnorm import _BatchNorm


class MultiStepContainer(nn.Sequential, base.MultiStepModule):
    def __init__(self, *args):
        super().__init__(*args)
        for m in self:
            assert not hasattr(m, 'step_mode') or m.step_mode == 's'
            if isinstance(m, base.StepModule):
                if 'm' in m.supported_step_mode():
                    logging.warning(f"{m} supports for step_mode == 's', which should not be contained by MultiStepContainer!")

    def forward(self, x_seq: Tensor):
        """
        :param x_seq: ``shape=[T, batch_size, ...]``
        :type x_seq: Tensor
        :return: y_seq with ``shape=[T, batch_size, ...]``
        :rtype: Tensor
        """
        return functional.multi_step_forward(x_seq, super().forward)


class SeqToANNContainer(nn.Sequential, base.MultiStepModule):
    def __init__(self, *args):
        super().__init__(*args)
        for m in self:
            assert not hasattr(m, 'step_mode') or m.step_mode == 's'
            if isinstance(m, base.StepModule):
                if 'm' in m.supported_step_mode():
                    logging.warning(f"{m} supports for step_mode == 's', which should not be contained by SeqToANNContainer!")

    def forward(self, x_seq: Tensor):
        """
        :param x_seq: shape=[T, batch_size, ...]
        :type x_seq: Tensor
        :return: y_seq, shape=[T, batch_size, ...]
        :rtype: Tensor
        """
        return functional.seq_to_ann_forward(x_seq, super().forward)


class StepModeContainer(nn.Sequential, base.StepModule):
    def __init__(self, stateful: bool, *args):
        super().__init__(*args)
        self.stateful = stateful
        for m in self:
            assert not hasattr(m, 'step_mode') or m.step_mode == 's'
            if isinstance(m, base.StepModule):
                if 'm' in m.supported_step_mode():
                    logging.warning(f"{m} supports for step_mode == 's', which should not be contained by StepModeContainer!")
        self.step_mode = 's'


    def forward(self, x: torch.Tensor):
        if self.step_mode == 's':
            return super().forward(x)
        elif self.step_mode == 'm':
            if self.stateful:
                return functional.multi_step_forward(x, super().forward)
            else:
                return functional.seq_to_ann_forward(x, super().forward)


class Conv2d(nn.Conv2d, base.StepModule):
    def __init__(
            self,
            in_channels: int,
            out_channels: int,
            kernel_size: _size_2_t,
            stride: _size_2_t = 1,
            padding: Union[str, _size_2_t] = 0,
            dilation: _size_2_t = 1,
            groups: int = 1,
            bias: bool = True,
            padding_mode: str = 'zeros',
            step_mode: str = 's'
    ) -> None:
        """
        * :ref:`API in English <Conv2d-en>`

        .. _Conv2d-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.Conv2d`

        * :ref:`?????? API <Conv2d-cn>`

        .. _Conv2d-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.Conv2d` for other parameters' API
        """
        super().__init__(in_channels, out_channels, kernel_size, stride, padding, dilation, groups, bias, padding_mode)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            x = super().forward(x)

        elif self.step_mode == 'm':
            if x.dim() != 5:
                raise ValueError(f'expected x with shape [T, N, C, H, W], but got x with shape {x.shape}!')
            x = functional.seq_to_ann_forward(x, super().forward)

        return x


class BatchNorm2d(nn.BatchNorm2d, base.StepModule):
    def __init__(
            self,
            num_features,
            eps=1e-5,
            momentum=0.1,
            affine=True,
            track_running_stats=True,
            step_mode='s'
    ):
        """
        * :ref:`API in English <BatchNorm2d-en>`

        .. _BatchNorm2d-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.BatchNorm2d`

        * :ref:`?????? API <BatchNorm2d-cn>`

        .. _BatchNorm2d-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.BatchNorm2d` for other parameters' API
        """
        super().__init__(num_features, eps, momentum, affine, track_running_stats)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            return super().forward(x)

        elif self.step_mode == 'm':
            if x.dim() != 5:
                raise ValueError(f'expected x with shape [T, N, C, H, W], but got x with shape {x.shape}!')
            return functional.seq_to_ann_forward(x, super().forward)

class GroupNorm(nn.GroupNorm, base.StepModule):
    def __init__(
            self,
            num_groups: int, num_channels: int, eps: float = 1e-5, affine: bool = True,
            step_mode='s'
    ):
        """
        * :ref:`API in English <GroupNorm-en>`

        .. _GroupNorm-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.GroupNorm`

        * :ref:`?????? API <GroupNorm-cn>`

        .. _GroupNorm-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.GroupNorm` for other parameters' API
        """
        super().__init__(num_groups, num_channels, eps, affine)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            return super().forward(x)

        elif self.step_mode == 'm':
            return functional.seq_to_ann_forward(x, super().forward)


class MaxPool2d(nn.MaxPool2d, base.StepModule):
    def __init__(self, kernel_size: _size_any_t, stride: Optional[_size_any_t] = None,
                 padding: _size_any_t = 0, dilation: _size_any_t = 1,
                 return_indices: bool = False, ceil_mode: bool = False, step_mode='s') -> None:
        """
        * :ref:`API in English <MaxPool2d-en>`

        .. _MaxPool2d-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.MaxPool2d`

        * :ref:`?????? API <MaxPool2d-cn>`

        .. _MaxPool2d-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.MaxPool2d` for other parameters' API
        """
        super().__init__(kernel_size, stride, padding, dilation, return_indices, ceil_mode)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            x = super().forward(x)

        elif self.step_mode == 'm':
            if x.dim() != 5:
                raise ValueError(f'expected x with shape [T, N, C, H, W], but got x with shape {x.shape}!')
            x = functional.seq_to_ann_forward(x, super().forward)

        return x

class AvgPool2d(nn.AvgPool2d, base.StepModule):
    def __init__(self, kernel_size: _size_2_t, stride: Optional[_size_2_t] = None, padding: _size_2_t = 0,
                 ceil_mode: bool = False, count_include_pad: bool = True, divisor_override: Optional[int] = None, step_mode='s') -> None:
        """
        * :ref:`API in English <AvgPool2d-en>`

        .. _AvgPool2d-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.AvgPool2d`

        * :ref:`?????? API <AvgPool2d-cn>`

        .. _AvgPool2d-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.AvgPool2d` for other parameters' API
        """
        super().__init__(kernel_size, stride, padding, ceil_mode, count_include_pad, divisor_override)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            x = super().forward(x)

        elif self.step_mode == 'm':
            if x.dim() != 5:
                raise ValueError(f'expected x with shape [T, N, C, H, W], but got x with shape {x.shape}!')
            x = functional.seq_to_ann_forward(x, super().forward)

        return x

class AdaptiveAvgPool2d(nn.AdaptiveAvgPool2d, base.StepModule):
    def __init__(self, output_size, step_mode='s') -> None:
        """
        * :ref:`API in English <AdaptiveAvgPool2d-en>`

        .. _AdaptiveAvgPool2d-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.AdaptiveAvgPool2d`

        * :ref:`?????? API <AdaptiveAvgPool2d-cn>`

        .. _AdaptiveAvgPool2d-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.AdaptiveAvgPool2d` for other parameters' API
        """
        super().__init__(output_size)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            x = super().forward(x)

        elif self.step_mode == 'm':
            if x.dim() != 5:
                raise ValueError(f'expected x with shape [T, N, C, H, W], but got x with shape {x.shape}!')
            x = functional.seq_to_ann_forward(x, super().forward)

        return x

class Linear(nn.Linear, base.StepModule):
    def __init__(self, in_features: int, out_features: int, bias: bool = True, step_mode='s') -> None:
        """
        * :ref:`API in English <Linear-en>`

        .. _Linear-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.Linear`

        * :ref:`?????? API <Linear-cn>`

        .. _Linear-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.Linear` for other parameters' API
        """
        super().__init__(in_features, out_features, bias)
        self.step_mode = step_mode


class Flatten(nn.Flatten, base.StepModule):
    def __init__(self, start_dim: int = 1, end_dim: int = -1, step_mode='s') -> None:
        """
        * :ref:`API in English <Flatten-en>`

        .. _Flatten-cn:

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????API?????? :class:`torch.nn.Flatten`

        * :ref:`?????? API <Flatten-cn>`

        .. _Flatten-en:

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        Refer to :class:`torch.nn.Flatten` for other parameters' API
        """
        super().__init__(start_dim, end_dim)
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f', step_mode={self.step_mode}'

    def forward(self, x: Tensor):
        if self.step_mode == 's':
            x = super().forward(x)

        elif self.step_mode == 'm':
            x = functional.seq_to_ann_forward(x, super().forward)
        return x


class NeuNorm(base.MemoryModule):
    def __init__(self, in_channels, height, width, k=0.9, shared_across_channels=False, step_mode='s'):
        """
        * :ref:`API in English <NeuNorm.__init__-en>`

        .. _NeuNorm.__init__-cn:

        :param in_channels: ????????????????????????

        :param height: ??????????????????

        :param width: ??????????????????

        :param k: ???????????????

        :param shared_across_channels: ?????????????????? ``w`` ???????????????????????????????????????????????? ``True`` ???????????????????????????

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        `Direct Training for Spiking Neural Networks: Faster, Larger, Better <https://arxiv.org/abs/1809.05793>`_ ?????????\\
        ???NeuNorm??????NeuNorm??????????????????????????????????????????????????????????????????

        ``Conv2d -> LIF -> NeuNorm``

        ???????????????????????? ``[batch_size, in_channels, height, width]``???

        ``in_channels`` ????????????NeuNorm??????????????????????????????????????? :math:`F`???

        ``k`` ?????????????????????????????????????????? :math:`k_{\\tau 2}`???

        ???????????? :math:`\\frac{v}{F}` ????????? :math:`k_{\\tau 2} + vF = 1` ???????????????

        * :ref:`??????API <NeuNorm.__init__-cn>`

        .. _NeuNorm.__init__-en:

        :param in_channels: channels of input

        :param height: height of input

        :param width: height of width

        :param k: momentum factor

        :param shared_across_channels: whether the learnable parameter ``w`` is shared over channel dim. If set ``True``,
            the consumption of memory can decrease largely

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        The NeuNorm layer is proposed in `Direct Training for Spiking Neural Networks: Faster, Larger, Better <https://arxiv.org/abs/1809.05793>`_.

        It should be placed after spiking neurons behind convolution layer, e.g.,

        ``Conv2d -> LIF -> NeuNorm``

        The input should be a 4-D tensor with ``shape = [batch_size, in_channels, height, width]``.

        ``in_channels`` is the channels of input???which is :math:`F` in the paper.

        ``k`` is the momentum factor???which is :math:`k_{\\tau 2}` in the paper.

        :math:`\\frac{v}{F}` will be calculated by :math:`k_{\\tau 2} + vF = 1` autonomously.

        """
        super().__init__()
        self.step_mode = step_mode
        self.register_memory('x', 0.)
        self.k0 = k
        self.k1 = (1. - self.k0) / in_channels ** 2
        if shared_across_channels:
            self.w = nn.Parameter(Tensor(1, height, width))
        else:
            self.w = nn.Parameter(Tensor(in_channels, height, width))
        nn.init.kaiming_uniform_(self.w, a=math.sqrt(5))

    def single_step_forward(self, in_spikes: Tensor):
        self.x = self.k0 * self.x + self.k1 * in_spikes.sum(dim=1,
                                                            keepdim=True)  # x.shape = [batch_size, 1, height, width]
        return in_spikes - self.w * self.x

    def extra_repr(self) -> str:
        return f'shape={self.w.shape}'


class Dropout(base.MemoryModule):
    def __init__(self, p=0.5, step_mode='s'):
        """
        * :ref:`API in English <Dropout.__init__-en>`

        .. _Dropout.__init__-cn:

        :param p: ????????????????????????0?????????
        :type p: float
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ??? ``torch.nn.Dropout`` ????????????????????????????????????????????????????????????????????????0?????????????????????????????????????????????????????????????????????reset()???\\
        ???????????????????????????????????????????????????????????????0???

        .. tip::

            ??????Dropout????????? `Enabling Spike-based Backpropagation for Training Deep Neural Network Architectures
            <https://arxiv.org/abs/1903.06379>`_ ???????????????????????????

            There is a subtle difference in the way dropout is applied in SNNs compared to ANNs. In ANNs, each epoch of
            training has several iterations of mini-batches. In each iteration, randomly selected units (with dropout ratio of :math:`p`)
            are disconnected from the network while weighting by its posterior probability (:math:`1-p`). However, in SNNs, each
            iteration has more than one forward propagation depending on the time length of the spike train. We back-propagate
            the output error and modify the network parameters only at the last time step. For dropout to be effective in
            our training method, it has to be ensured that the set of connected units within an iteration of mini-batch
            data is not changed, such that the neural network is constituted by the same random subset of units during
            each forward propagation within a single iteration. On the other hand, if the units are randomly connected at
            each time-step, the effect of dropout will be averaged out over the entire forward propagation time within an
            iteration. Then, the dropout effect would fade-out once the output error is propagated backward and the parameters
            are updated at the last time step. Therefore, we need to keep the set of randomly connected units for the entire
            time window within an iteration.

        * :ref:`??????API <Dropout.__init__-cn>`

        .. _Dropout.__init__-en:

        :param p: probability of an element to be zeroed
        :type p: float
        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        This layer is almost same with ``torch.nn.Dropout``. The difference is that elements have been zeroed at first
        step during a simulation will always be zero. The indexes of zeroed elements will be update only after ``reset()``
        has been called and a new simulation is started.

        .. admonition:: Tip
            :class: tip

            This kind of Dropout is firstly described in `Enabling Spike-based Backpropagation for Training Deep Neural
            Network Architectures <https://arxiv.org/abs/1903.06379>`_:

            There is a subtle difference in the way dropout is applied in SNNs compared to ANNs. In ANNs, each epoch of
            training has several iterations of mini-batches. In each iteration, randomly selected units (with dropout ratio of :math:`p`)
            are disconnected from the network while weighting by its posterior probability (:math:`1-p`). However, in SNNs, each
            iteration has more than one forward propagation depending on the time length of the spike train. We back-propagate
            the output error and modify the network parameters only at the last time step. For dropout to be effective in
            our training method, it has to be ensured that the set of connected units within an iteration of mini-batch
            data is not changed, such that the neural network is constituted by the same random subset of units during
            each forward propagation within a single iteration. On the other hand, if the units are randomly connected at
            each time-step, the effect of dropout will be averaged out over the entire forward propagation time within an
            iteration. Then, the dropout effect would fade-out once the output error is propagated backward and the parameters
            are updated at the last time step. Therefore, we need to keep the set of randomly connected units for the entire
            time window within an iteration.
        """
        super().__init__()
        self.step_mode = step_mode
        assert 0 <= p < 1
        self.register_memory('mask', None)
        self.p = p

    def extra_repr(self):
        return f'p={self.p}'

    def create_mask(self, x: Tensor):
        self.mask = F.dropout(torch.ones_like(x.data), self.p, training=True)

    def single_step_forward(self, x: Tensor):
        if self.training:
            if self.mask is None:
                self.create_mask(x)

            return x * self.mask
        else:
            return x

    def multi_step_forward(self, x_seq: Tensor):
        if self.training:
            if self.mask is None:
                self.create_mask(x_seq[0])

            return x_seq * self.mask
        else:
            return x_seq


class Dropout2d(Dropout):
    def __init__(self, p=0.2, step_mode='s'):
        """
        * :ref:`API in English <Dropout2d.__init__-en>`

        .. _Dropout2d.__init__-cn:

        :param p: ????????????????????????0?????????
        :type p: float
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ??? ``torch.nn.Dropout2d`` ????????????????????????????????????????????????????????????????????????0?????????????????????????????????????????????????????????????????????reset()???\\
        ???????????????????????????????????????????????????????????????0???

        ??????SNN???Dropout???????????????????????? :ref:`layer.Dropout <Dropout.__init__-cn>`???

        * :ref:`??????API <Dropout2d.__init__-cn>`

        .. _Dropout2d.__init__-en:

        :param p: probability of an element to be zeroed
        :type p: float
        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        This layer is almost same with ``torch.nn.Dropout2d``. The difference is that elements have been zeroed at first
        step during a simulation will always be zero. The indexes of zeroed elements will be update only after ``reset()``
        has been called and a new simulation is started.

        For more information about Dropout in SNN, refer to :ref:`layer.Dropout <Dropout.__init__-en>`.
        """
        super().__init__(p, step_mode)

    def create_mask(self, x: Tensor):
        self.mask = F.dropout2d(torch.ones_like(x.data), self.p, training=True)


class SynapseFilter(base.MemoryModule):
    def __init__(self, tau=100.0, learnable=False, step_mode='s'):
        """
        * :ref:`API in English <LowPassSynapse.__init__-en>`

        .. _LowPassSynapse.__init__-cn:

        :param tau: time ????????????????????????????????????

        :param learnable: ???????????????????????????????????????????????????????????? ``True``?????? ``tau`` ???????????????????????????????????????

        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ??????????????????????????????????????????????????????????????????????????????????????????????????????????????????

        .. math::
            \\tau \\frac{\\mathrm{d} I(t)}{\\mathrm{d} t} = - I(t)

        ?????????????????????????????????????????????1???

        .. math::
            I(t) = I(t) + 1

        ?????????????????? :math:`S(t)`??????????????????????????????????????????????????????

        .. math::
            I(t) = I(t-1) - (1 - S(t)) \\frac{1}{\\tau} I(t-1) + S(t)

        ????????????????????????????????????????????????????????????????????????????????????

        .. code-block:: python

            T = 50
            in_spikes = (torch.rand(size=[T]) >= 0.95).float()
            lp_syn = LowPassSynapse(tau=10.0)
            pyplot.subplot(2, 1, 1)
            pyplot.bar(torch.arange(0, T).tolist(), in_spikes, label='in spike')
            pyplot.xlabel('t')
            pyplot.ylabel('spike')
            pyplot.legend()

            out_i = []
            for i in range(T):
                out_i.append(lp_syn(in_spikes[i]))
            pyplot.subplot(2, 1, 2)
            pyplot.plot(out_i, label='out i')
            pyplot.xlabel('t')
            pyplot.ylabel('i')
            pyplot.legend()
            pyplot.show()

        .. image:: ../_static/API/activation_based/layer/SynapseFilter.png

        ?????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

        ????????????????????????????????????

        `Unsupervised learning of digit recognition using spike-timing-dependent plasticity <https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full>`_

        `Exploiting Neuron and Synapse Filter Dynamics in Spatial Temporal Learning of Deep Spiking Neural Network <https://arxiv.org/abs/2003.02944>`_

        ???????????????????????????????????????????????????????????????????????????LIF???????????????????????????????????????????????? :math:`+\\infty` ???

        ???????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????

        `Enabling spike-based backpropagation for training deep neural network architectures <https://arxiv.org/abs/1903.06379>`_

        * :ref:`??????API <LowPassSynapse.__init__-cn>`

        .. _LowPassSynapse.__init__-en:

        :param tau: time constant that determines the decay rate of current in the synapse

        :param learnable: whether time constant is learnable during training. If ``True``, then ``tau`` will be the
            initial value of time constant

        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        The synapse filter that can filter input current. The output current will decay when there is no input spike:

        .. math::
            \\tau \\frac{\\mathrm{d} I(t)}{\\mathrm{d} t} = - I(t)

        The output current will increase 1 when there is a new input spike:

        .. math::
            I(t) = I(t) + 1

        Denote the input spike as :math:`S(t)`, then the discrete current update equation is as followed:

        .. math::
            I(t) = I(t-1) - (1 - S(t)) \\frac{1}{\\tau} I(t-1) + S(t)

        This synapse can smooth input. Here is the example and output:

        .. code-block:: python

            T = 50
            in_spikes = (torch.rand(size=[T]) >= 0.95).float()
            lp_syn = LowPassSynapse(tau=10.0)
            pyplot.subplot(2, 1, 1)
            pyplot.bar(torch.arange(0, T).tolist(), in_spikes, label='in spike')
            pyplot.xlabel('t')
            pyplot.ylabel('spike')
            pyplot.legend()

            out_i = []
            for i in range(T):
                out_i.append(lp_syn(in_spikes[i]))
            pyplot.subplot(2, 1, 2)
            pyplot.plot(out_i, label='out i')
            pyplot.xlabel('t')
            pyplot.ylabel('i')
            pyplot.legend()
            pyplot.show()

        .. image:: ../_static/API/activation_based/layer/SynapseFilter.png

        The output current is not only determined by the present input but also by the previous input, which makes this
        synapse have memory.

        This synapse is sometimes used, e.g.:

        `Unsupervised learning of digit recognition using spike-timing-dependent plasticity <https://www.frontiersin.org/articles/10.3389/fncom.2015.00099/full>`_

        `Exploiting Neuron and Synapse Filter Dynamics in Spatial Temporal Learning of Deep Spiking Neural Network <https://arxiv.org/abs/2003.02944>`_

        Another view is regarding this synapse as a LIF neuron with a :math:`+\\infty` threshold voltage.

        The final output of this synapse (or the final voltage of this LIF neuron) represents the accumulation of input
        spikes, which substitute for traditional firing rate that indicates the excitatory level. So, it can be used in
        the last layer of the network, e.g.:

        `Enabling spike-based backpropagation for training deep neural network architectures <https://arxiv.org/abs/1903.06379>`_

        """
        super().__init__()
        self.step_mode = step_mode
        self.learnable = learnable
        assert tau > 1
        if learnable:
            init_w = - math.log(tau - 1)
            self.w = nn.Parameter(torch.as_tensor(init_w))
        else:
            self.tau = tau

        self.register_memory('out_i', 0.)

    def extra_repr(self):
        if self.learnable:
            with torch.no_grad():
                tau = 1. / self.w.sigmoid()
        else:
            tau = self.tau

        return f'tau={tau}, learnable={self.learnable}, step_mode={self.step_mode}'

    @staticmethod
    @torch.jit.script
    def js_single_step_forward_learnable(x: torch.Tensor, w: torch.Tensor, out_i: torch.Tensor):
        inv_tau = w.sigmoid()
        out_i = out_i - (1. - x) * out_i * inv_tau + x
        return out_i

    @staticmethod
    @torch.jit.script
    def js_single_step_forward(x: torch.Tensor, tau: float, out_i: torch.Tensor):
        inv_tau = 1. / tau
        out_i = out_i - (1. - x) * out_i * inv_tau + x
        return out_i

    def single_step_forward(self, x: Tensor):
        if isinstance(self.out_i, float):
            out_i_init = self.out_i
            self.out_i = torch.zeros_like(x.data)
            if out_i_init != 0.:
                torch.fill_(self.out_i, out_i_init)

        if self.learnable:
            self.out_i = self.js_single_step_forward_learnable(x, self.w, self.out_i)
        else:
            self.out_i = self.js_single_step_forward(x, self.tau, self.out_i)
        return self.out_i


class DropConnectLinear(base.MemoryModule):
    def __init__(self, in_features: int, out_features: int, bias: bool = True, p: float = 0.5, samples_num: int = 1024,
                 invariant: bool = False, activation: None or nn.Module = nn.ReLU(), state_mode='s') -> None:
        """
        * :ref:`API in English <DropConnectLinear.__init__-en>`

        .. _DropConnectLinear.__init__-cn:

        :param in_features: ??????????????????????????????
        :type in_features: int
        :param out_features: ??????????????????????????????
        :type out_features: int
        :param bias: ?????? ``False``?????????????????????????????????????????????
            ????????? ``True``
        :type bias: bool
        :param p: ??????????????????????????????????????????0.5
        :type p: float
        :param samples_num: ??????????????????????????????????????????????????????????????????1024
        :type samples_num: int
        :param invariant: ?????? ``True``?????????????????????????????????????????????????????????????????????????????????????????????????????????????????? ``reset()`` ??????
            ??????????????????????????????????????????????????????????????????????????????????????? ``reset()`` ??????????????????????????????????????????????????????????????? ??????
            ``False``??????????????????????????????????????????????????????????????????????????????????????? ?????? :ref:`layer.Dropout <Dropout.__init__-cn>` ???
            ???????????????????????????????????????
            ????????? ``False``
        :type invariant: bool
        :param activation: ???????????????????????????
        :type activation: None or nn.Module
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        DropConnect?????? `Regularization of Neural Networks using DropConnect <http://proceedings.mlr.press/v28/wan13.pdf>`_
        ???????????????DropConnect???Dropout???????????????????????????DropConnect???????????? ``p`` ??????????????????Dropout????????????????????????0???

        .. Note::

            ?????????DropConnect???????????????????????????tensor??????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????????
            ???????????????????????? `Regularization of Neural Networks using DropConnect <http://proceedings.mlr.press/v28/wan13.pdf>`_
            ???????????? `Algorithm 2` ?????????????????? ``activation`` ????????????????????????????????????????????????????????????????????????

        * :ref:`??????API <DropConnectLinear.__init__-cn>`

        .. _DropConnectLinear.__init__-en:

        :param in_features: size of each input sample
        :type in_features: int
        :param out_features: size of each output sample
        :type out_features: int
        :param bias: If set to ``False``, the layer will not learn an additive bias.
            Default: ``True``
        :type bias: bool
        :param p: probability of an connection to be zeroed. Default: 0.5
        :type p: float
        :param samples_num: number of samples drawn from the Gaussian during inference. Default: 1024
        :type samples_num: int
        :param invariant: If set to ``True``, the connections will be dropped at the first time of forward and the dropped
            connections will remain unchanged until ``reset()`` is called and the connections recovery to fully-connected
            status. Then the connections will be re-dropped at the first time of forward after ``reset()``. If set to
            ``False``, the connections will be re-dropped at every forward. See :ref:`layer.Dropout <Dropout.__init__-en>`
            for more information to understand this parameter. Default: ``False``
        :type invariant: bool
        :param activation: the activation layer after the linear layer
        :type activation: None or nn.Module
        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        DropConnect, which is proposed by `Regularization of Neural Networks using DropConnect <http://proceedings.mlr.press/v28/wan13.pdf>`_,
        is similar with Dropout but drop connections of a linear layer rather than the elements of the input tensor with
        probability ``p``.

        .. admonition:: Note
            :class: note

            When inference with DropConnect, every elements of the output tensor are sampled from a Gaussian distribution,
            activated by the activation layer and averaged over the sample number ``samples_num``.
            See `Algorithm 2` in `Regularization of Neural Networks using DropConnect <http://proceedings.mlr.press/v28/wan13.pdf>`_
            for more details. Note that activation is an intermediate process. This is the reason why we include
            ``activation`` as a member variable of this module.
        """
        super().__init__()
        self.state_mode = state_mode
        self.in_features = in_features
        self.out_features = out_features
        self.weight = nn.Parameter(Tensor(out_features, in_features))
        if bias:
            self.bias = nn.Parameter(Tensor(out_features))
        else:
            self.register_parameter('bias', None)

        self.reset_parameters()

        self.p = p  # ???0?????????
        self.register_memory('dropped_w', None)
        if self.bias is not None:
            self.register_memory('dropped_b', None)

        self.samples_num = samples_num
        self.invariant = invariant
        self.activation = activation

    def reset_parameters(self) -> None:
        """
        * :ref:`API in English <DropConnectLinear.reset_parameters-en>`

        .. _DropConnectLinear.reset_parameters-cn:

        :return: None
        :rtype: None

        ???????????????????????????????????????

        * :ref:`??????API <DropConnectLinear.reset_parameters-cn>`

        .. _DropConnectLinear.reset_parameters-en:

        :return: None
        :rtype: None

        Initialize the learnable parameters of this module.
        """
        nn.init.kaiming_uniform_(self.weight, a=math.sqrt(5))
        if self.bias is not None:
            fan_in, _ = nn.init._calculate_fan_in_and_fan_out(self.weight)
            bound = 1 / math.sqrt(fan_in)
            nn.init.uniform_(self.bias, -bound, bound)

    def reset(self):
        """
        * :ref:`API in English <DropConnectLinear.reset-en>`

        .. _DropConnectLinear.reset-cn:

        :return: None
        :rtype: None

        ???????????????????????????????????????????????? ``self.activation`` ???????????????????????????????????????????????????

        * :ref:`??????API <DropConnectLinear.reset-cn>`

        .. _DropConnectLinear.reset-en:

        :return: None
        :rtype: None

        Reset the linear layer to fully-connected status. If ``self.activation`` is also stateful, this function will
        also reset it.
        """
        super().reset()
        if hasattr(self.activation, 'reset'):
            self.activation.reset()

    def drop(self, batch_size: int):
        mask_w = (torch.rand_like(self.weight.unsqueeze(0).repeat([batch_size] + [1] * self.weight.dim())) > self.p)
        # self.dropped_w = mask_w.to(self.weight) * self.weight  # shape = [batch_size, out_features, in_features]
        self.dropped_w = self.weight * mask_w

        if self.bias is not None:
            mask_b = (torch.rand_like(self.bias.unsqueeze(0).repeat([batch_size] + [1] * self.bias.dim())) > self.p)
            # self.dropped_b = mask_b.to(self.bias) * self.bias
            self.dropped_b = self.bias * mask_b

    def single_step_forward(self, input: Tensor) -> Tensor:
        if self.training:
            if self.invariant:
                if self.dropped_w is None:
                    self.drop(input.shape[0])
            else:
                self.drop(input.shape[0])
            if self.bias is None:
                ret = torch.bmm(self.dropped_w, input.unsqueeze(-1)).squeeze(-1)
            else:
                ret = torch.bmm(self.dropped_w, input.unsqueeze(-1)).squeeze(-1) + self.dropped_b
            if self.activation is None:
                return ret
            else:
                return self.activation(ret)
        else:
            mu = (1 - self.p) * F.linear(input, self.weight, self.bias)  # shape = [batch_size, out_features]
            if self.bias is None:
                sigma2 = self.p * (1 - self.p) * F.linear(input.square(), self.weight.square())
            else:
                sigma2 = self.p * (1 - self.p) * F.linear(input.square(), self.weight.square(), self.bias.square())
            dis = torch.distributions.normal.Normal(mu, sigma2.sqrt())
            samples = dis.sample(torch.Size([self.samples_num]))

            if self.activation is None:
                ret = samples
            else:
                ret = self.activation(samples)
            return ret.mean(dim=0)

    def extra_repr(self) -> str:
        return f'in_features={self.in_features}, out_features={self.out_features}, bias={self.bias is not None}, p={self.p}, invariant={self.invariant}'



class PrintShapeModule(nn.Module):
    def __init__(self, ext_str='PrintShapeModule'):
        """
        * :ref:`API in English <PrintModule.__init__-en>`

        .. _PrintModule.__init__-cn:

        :param ext_str: ????????????????????????
        :type ext_str: str

        ????????? ``ext_str`` ???????????? ``shape``???????????????????????????????????????????????????debug???

        * :ref:`??????API <PrintModule.__init__-cn>`

        .. _PrintModule.__init__-en:

        :param ext_str: extra strings for printing
        :type ext_str: str

        This layer will not do any operation but print ``ext_str`` and the shape of input, which can be used for debugging.

        """
        super().__init__()
        self.ext_str = ext_str

    def forward(self, x: Tensor):
        print(self.ext_str, x.shape)
        return x


class ElementWiseRecurrentContainer(base.MemoryModule):
    def __init__(self, sub_module: nn.Module, element_wise_function: Callable, step_mode='s'):
        """
        * :ref:`API in English <ElementWiseRecurrentContainer-en>`

        .. _ElementWiseRecurrentContainer-cn:

        :param sub_module: ??????????????????
        :type sub_module: torch.nn.Module
        :param element_wise_function: ???????????????????????????????????????????????? ``z=f(x, y)``
        :type element_wise_function: Callable
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ???????????????????????????????????????????????? ``sub_module`` ?????????????????? :math:`i[t]` ??? :math:`y[t]` ????????? :math:`y[t]` ?????????????????????????????????
        ???????????????????????? :math:`x[t]`??????

        .. math::

            i[t] = f(x[t], y[t-1])

        ?????? :math:`f` ??????????????????????????????????????????????????? :math:`y[-1] = 0`???


        .. Note::

            ``sub_module`` ???????????????????????????????????????

        ???????????????

        .. code-block:: python

            T = 8
            net = ElementWiseRecurrentContainer(neuron.IFNode(v_reset=None), element_wise_function=lambda x, y: x + y)
            print(net)
            x = torch.zeros([T])
            x[0] = 1.5
            for t in range(T):
                print(t, f'x[t]={x[t]}, s[t]={net(x[t])}')

            functional.reset_net(net)


        * :ref:`?????? API <ElementWiseRecurrentContainer-cn>`

        .. _ElementWiseRecurrentContainer-en:

        :param sub_module: the contained module
        :type sub_module: torch.nn.Module
        :param element_wise_function: the user-defined element-wise function, which should have the format ``z=f(x, y)``
        :type element_wise_function: Callable
        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        A container that use a element-wise recurrent connection. Denote the inputs and outputs of ``sub_module`` as :math:`i[t]`
        and :math:`y[t]` (Note that :math:`y[t]` is also the outputs of this module), and the inputs of this module as
        :math:`x[t]`, then

        .. math::

            i[t] = f(x[t], y[t-1])

        where :math:`f` is the user-defined element-wise function. We set :math:`y[-1] = 0`.

        .. admonition:: Note
            :class: note

            The shape of inputs and outputs of ``sub_module`` must be the same.

        Codes example:

        .. code-block:: python

            T = 8
            net = ElementWiseRecurrentContainer(neuron.IFNode(v_reset=None), element_wise_function=lambda x, y: x + y)
            print(net)
            x = torch.zeros([T])
            x[0] = 1.5
            for t in range(T):
                print(t, f'x[t]={x[t]}, s[t]={net(x[t])}')

            functional.reset_net(net)
        """
        super().__init__()
        self.step_mode = step_mode
        assert not hasattr(sub_module, 'step_mode') or sub_module.step_mode == 's'
        self.sub_module = sub_module
        self.element_wise_function = element_wise_function
        self.register_memory('y', None)

    def single_step_forward(self, x: Tensor):
        if self.y is None:
            self.y = torch.zeros_like(x.data)
        self.y = self.sub_module(self.element_wise_function(self.y, x))
        return self.y

    def extra_repr(self) -> str:
        return f'element-wise function={self.element_wise_function}, step_mode={self.step_mode}'


class LinearRecurrentContainer(base.MemoryModule):
    def __init__(self, sub_module: nn.Module, in_features: int, out_features: int, bias: bool = True,
                 step_mode='s') -> None:
        """
        * :ref:`API in English <LinearRecurrentContainer-en>`

        .. _LinearRecurrentContainer-cn:

        :param sub_module: ??????????????????
        :type sub_module: torch.nn.Module
        :param in_features: ?????????????????????
        :type in_features: int
        :param out_features: ?????????????????????
        :type out_features: int
        :param bias: ?????? ``False``??????????????????????????????????????????????????????
        :type bias: bool
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ?????????????????????????????????????????? ``sub_module`` ????????????????????? :math:`i[t]` ??? :math:`y[t]` ????????? :math:`y[t]` ?????????????????????????????????
        ??????????????????????????? :math:`x[t]` ??????

        .. math::

            i[t] = \\begin{pmatrix} x[t] \\\\ y[t-1]\\end{pmatrix} W^{T} + b

        ?????? :math:`W, b` ?????????????????????????????????????????? :math:`y[-1] = 0`???

        :math:`x[t]` ?????? ``shape = [N, *, in_features]``???:math:`y[t]` ????????? ``shape = [N, *, out_features]``???

        .. Note::

            ??????????????? ``torch.nn.Linear(in_features + out_features, in_features, bias)`` ????????????

        .. code-block:: python

            in_features = 4
            out_features = 2
            T = 8
            N = 2
            net = LinearRecurrentContainer(
                nn.Sequential(
                    nn.Linear(in_features, out_features),
                    neuron.LIFNode(),
                ),
                in_features, out_features)
            print(net)
            x = torch.rand([T, N, in_features])
            for t in range(T):
                print(t, net(x[t]))

            functional.reset_net(net)

        * :ref:`?????? API <LinearRecurrentContainer-cn>`

        .. _LinearRecurrentContainer-en:

        :param sub_module: the contained module
        :type sub_module: torch.nn.Module
        :param in_features: size of each input sample
        :type in_features: int
        :param out_features: size of each output sample
        :type out_features: int
        :param bias: If set to ``False``, the linear recurrent layer will not learn an additive bias
        :type bias: bool
        :param step_mode: the step mode, which can be `s` (single-step) or `m` (multi-step)
        :type step_mode: str

        A container that use a linear recurrent connection. Denote the inputs and outputs of ``sub_module`` as :math:`i[t]`
        and :math:`y[t]` (Note that :math:`y[t]` is also the outputs of this module), and the inputs of this module as
        :math:`x[t]`, then

        .. math::

            i[t] = \\begin{pmatrix} x[t] \\\\ y[t-1]\\end{pmatrix} W^{T} + b

        where :math:`W, b` are the weight and bias of the linear connection. We set :math:`y[-1] = 0`.

        :math:`x[t]` should have the shape ``[N, *, in_features]``, and :math:`y[t]` has the shape ``[N, *, out_features]``.

        .. admonition:: Note
            :class: note

            The recurrent connection is implement by ``torch.nn.Linear(in_features + out_features, in_features, bias)``.

        .. code-block:: python

            in_features = 4
            out_features = 2
            T = 8
            N = 2
            net = LinearRecurrentContainer(
                nn.Sequential(
                    nn.Linear(in_features, out_features),
                    neuron.LIFNode(),
                ),
                in_features, out_features)
            print(net)
            x = torch.rand([T, N, in_features])
            for t in range(T):
                print(t, net(x[t]))

            functional.reset_net(net)

        """
        super().__init__()
        self.step_mode = step_mode
        assert not hasattr(sub_module, 'step_mode') or sub_module.step_mode == 's'
        self.sub_module_out_features = out_features
        self.rc = nn.Linear(in_features + out_features, in_features, bias)
        self.sub_module = sub_module
        self.register_memory('y', None)

    def single_step_forward(self, x: Tensor):
        if self.y is None:
            if x.ndim == 2:
                self.y = torch.zeros([x.shape[0], self.sub_module_out_features]).to(x)
            else:
                out_shape = [x.shape[0]]
                out_shape.extend(x.shape[1:-1])
                out_shape.append(self.sub_module_out_features)
                self.y = torch.zeros(out_shape).to(x)
        x = torch.cat((x, self.y), dim=-1)
        self.y = self.sub_module(self.rc(x))
        return self.y

    def extra_repr(self) -> str:
        return f', step_mode={self.step_mode}'

class _ThresholdDependentBatchNormBase(_BatchNorm, base.MultiStepModule):
    def __init__(self, alpha: float, v_th: float, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.step_mode = 'm'
        self.alpha = alpha
        self.v_th = v_th
        assert self.affine, "ThresholdDependentBatchNorm needs to set `affine = True`!"
        torch.nn.init.constant_(self.weight, alpha * v_th)

    def forward(self, x_seq):
        return functional.seq_to_ann_forward(x_seq, super().forward)


class ThresholdDependentBatchNorm1d(_ThresholdDependentBatchNormBase):
    def __init__(self, alpha: float, v_th: float, *args, **kwargs):
        """
        * :ref:`API in English <MultiStepThresholdDependentBatchNorm1d.__init__-en>`

        .. _MultiStepThresholdDependentBatchNorm1d.__init__-cn:

        :param alpha: ?????????????????????????????????
        :type alpha: float
        :param v_th: ????????????????????????????????????
        :type v_th: float

        ``*args, **kwargs`` ??????????????? :class:`torch.nn.BatchNorm1d` ??????????????????

        `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_ ????????????
        ???Threshold-Dependent Batch Normalization (tdBN)???

        * :ref:`??????API <MultiStepThresholdDependentBatchNorm1d.__init__-cn>`

        .. _MultiStepThresholdDependentBatchNorm1d.__init__-en:

        :param alpha: the hyper-parameter depending on network structure
        :type alpha: float
        :param v_th: the threshold of next spiking neurons layer
        :type v_th: float

        Other parameters in ``*args, **kwargs`` are same with those of :class:`torch.nn.BatchNorm1d`.

        The Threshold-Dependent Batch Normalization (tdBN) proposed in `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_.
        """
        super().__init__(alpha, v_th, *args, **kwargs)


class ThresholdDependentBatchNorm2d(_ThresholdDependentBatchNormBase):
    def __init__(self, alpha: float, v_th: float, *args, **kwargs):
        """
        * :ref:`API in English <MultiStepThresholdDependentBatchNorm2d.__init__-en>`

        .. _MultiStepThresholdDependentBatchNorm2d.__init__-cn:

        :param alpha: ?????????????????????????????????
        :type alpha: float
        :param v_th: ????????????????????????????????????
        :type v_th: float

        ``*args, **kwargs`` ??????????????? :class:`torch.nn.BatchNorm2d` ??????????????????

        `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_ ????????????
        ???Threshold-Dependent Batch Normalization (tdBN)???

        * :ref:`??????API <MultiStepThresholdDependentBatchNorm2d.__init__-cn>`

        .. _MultiStepThresholdDependentBatchNorm2d.__init__-en:

        :param alpha: the hyper-parameter depending on network structure
        :type alpha: float
        :param v_th: the threshold of next spiking neurons layer
        :type v_th: float

        Other parameters in ``*args, **kwargs`` are same with those of :class:`torch.nn.BatchNorm2d`.

        The Threshold-Dependent Batch Normalization (tdBN) proposed in `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_.
        """
        super().__init__(alpha, v_th, *args, **kwargs)


class ThresholdDependentBatchNorm3d(_ThresholdDependentBatchNormBase):
    def __init__(self, alpha: float, v_th: float, *args, **kwargs):
        """
        * :ref:`API in English <MultiStepThresholdDependentBatchNorm3d.__init__-en>`

        .. _MultiStepThresholdDependentBatchNorm3d.__init__-cn:

        :param alpha: ?????????????????????????????????
        :type alpha: float
        :param v_th: ????????????????????????????????????
        :type v_th: float

        ``*args, **kwargs`` ??????????????? :class:`torch.nn.BatchNorm3d` ??????????????????

        `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_ ????????????
        ???Threshold-Dependent Batch Normalization (tdBN)???

        * :ref:`??????API <MultiStepThresholdDependentBatchNorm3d.__init__-cn>`

        .. _MultiStepThresholdDependentBatchNorm3d.__init__-en:

        :param alpha: the hyper-parameter depending on network structure
        :type alpha: float
        :param v_th: the threshold of next spiking neurons layer
        :type v_th: float

        Other parameters in ``*args, **kwargs`` are same with those of :class:`torch.nn.BatchNorm3d`.

        The Threshold-Dependent Batch Normalization (tdBN) proposed in `Going Deeper With Directly-Trained Larger Spiking Neural Networks <https://arxiv.org/abs/2011.05280>`_.
        """
        super().__init__(alpha, v_th, *args, **kwargs)


class TemporalWiseAttention(base.MultiStepModule):
    def __init__(self, T: int, reduction: int = 16, dimension: int = 4):
        """
        * :ref:`API in English <MultiStepTemporalWiseAttention.__init__-en>`

        .. _MultiStepTemporalWiseAttention.__init__-cn:

        :param T: ???????????????????????????

        :param reduction: ?????????

        :param dimension: ??????????????????????????????????????????[T, N, C, H, W]?????? dimension = 4????????????????????????[T, N, L]??????dimension = 2???

        `Temporal-Wise Attention Spiking Neural Networks for Event Streams Classification <https://openaccess.thecvf.com/content/ICCV2021/html/Yao_Temporal-Wise_Attention_Spiking_Neural_Networks_for_Event_Streams_Classification_ICCV_2021_paper.html>`_ ?????????
        ???MultiStepTemporalWiseAttention??????MultiStepTemporalWiseAttention?????????????????????????????????????????????????????????????????????

        ``Conv2d -> MultiStepTemporalWiseAttention -> LIF``

        ?????????????????? ``[T, N, C, H, W]`` ?????? ``[T, N, L]`` ?????????MultiStepTemporalWiseAttention??????????????? ``[T, N, C, H, W]`` ?????? ``[T, N, L]`` ???

        ``reduction`` ???????????????????????????????????? :math:`r`???

        * :ref:`??????API <MultiStepTemporalWiseAttention.__init__-cn>`

        .. _MultiStepTemporalWiseAttention.__init__-en:

        :param T: timewindows of input

        :param reduction: reduction ratio

        :param dimension: Dimensions of input. If the input dimension is [T, N, C, H, W], dimension = 4; when the input dimension is [T, N, L], dimension = 2.

        The MultiStepTemporalWiseAttention layer is proposed in `Temporal-Wise Attention Spiking Neural Networks for Event Streams Classification <https://openaccess.thecvf.com/content/ICCV2021/html/Yao_Temporal-Wise_Attention_Spiking_Neural_Networks_for_Event_Streams_Classification_ICCV_2021_paper.html>`_.

        It should be placed after the convolution layer and before the spiking neurons, e.g.,

        ``Conv2d -> MultiStepTemporalWiseAttention -> LIF``

        The dimension of the input is ``[T, N, C, H, W]`` or  ``[T, N, L]`` , after the MultiStepTemporalWiseAttention layer, the output dimension is ``[T, N, C, H, W]`` or  ``[T, N, L]`` .

        ``reduction`` is the reduction ratio???which is :math:`r` in the paper.

        """
        super().__init__()
        self.step_mode = 'm'
        assert dimension == 4 or dimension == 2, 'dimension must be 4 or 2'

        self.dimension = dimension

        # Sequence
        if self.dimension == 2:
            self.avg_pool = nn.AdaptiveAvgPool1d(1)
            self.max_pool = nn.AdaptiveMaxPool1d(1)
        elif self.dimension == 4:
            self.avg_pool = nn.AdaptiveAvgPool3d(1)
            self.max_pool = nn.AdaptiveMaxPool3d(1)

        assert T >= reduction, 'reduction cannot be greater than T'

        # Excitation
        self.sharedMLP = nn.Sequential(
            nn.Linear(T, T // reduction, bias=False),
            nn.ReLU(),
            nn.Linear(T // reduction, T, bias=False)
        )

        self.sigmoid = nn.Sigmoid()

    def forward(self, x_seq: torch.Tensor):
        assert x_seq.dim() == 3 or x_seq.dim() == 5, ValueError(
            f'expected 3D or 5D input with shape [T, N, M] or [T, N, C, H, W], but got input with shape {x_seq.shape}')
        x_seq = x_seq.transpose(0, 1)
        avgout = self.sharedMLP(self.avg_pool(x_seq).view([x_seq.shape[0], x_seq.shape[1]]))
        maxout = self.sharedMLP(self.max_pool(x_seq).view([x_seq.shape[0], x_seq.shape[1]]))
        scores = self.sigmoid(avgout + maxout)
        if self.dimension == 2:
            y_seq = x_seq * scores[:, :, None]
        elif self.dimension == 4:
            y_seq = x_seq * scores[:, :, None, None, None]
        y_seq = y_seq.transpose(0, 1)
        return y_seq


class VotingLayer(nn.Module, base.StepModule):
    def __init__(self, voting_size: int = 10, step_mode='s'):
        """
        * :ref:`API in English <VotingLayer-en>`

        .. _VotingLayer-cn:

        :param voting_size: ?????????????????????????????????
        :type voting_size: int
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        ??????????????? ``shape = [..., C * voting_size]`` ?????????????????????????????? ``kernel_size = voting_size, stride = voting_size`` ???????????????

        * :ref:`?????? API <VotingLayer-cn>`

        .. _VotingLayer-en:

        :param voting_size: the voting numbers for determine a class
        :type voting_size: int
        :param step_mode: ???????????????????????? `'s'` (??????) ??? `'m'` (??????)
        :type step_mode: str

        Applies average pooling with ``kernel_size = voting_size, stride = voting_size`` on the last dimension of the input with ``shape = [..., C * voting_size]``

        """
        super().__init__()
        self.voting_size = voting_size
        self.step_mode = step_mode

    def extra_repr(self):
        return super().extra_repr() + f'voting_size={self.voting_size}, step_mode={self.step_mode}'

    def single_step_forward(self, x: torch.Tensor):
        return F.avg_pool1d(x.unsqueeze(1), self.voting_size, self.voting_size).squeeze(1)

    def forward(self, x: torch.Tensor):
        if self.step_mode == 's':
            return self.single_step_forward(x)
        elif self.step_mode == 'm':
            return functional.seq_to_ann_forward(x, self.single_step_forward)
