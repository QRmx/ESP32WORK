For basic usage, please refer to the [wiki page](https://github.com/dinhhuy2109/python-cope/wiki)

<!---
# Basic usage
## On the covariance of X in the AX=XB
The classical hand-eye calibration problem consists in identifying the rigidbody
transformation eTc between a camera mounted on the end-effector of
a robot and the end-effector itself (see the below figure). The problem is usually framed as the AX=XB problem. In this functionality, we provide a solution not only solving for X but also predicting the covariance of X from those of A and B, where A and B are now randomly perturbed transformation matrices. 

For more details, please refer to the accompanying paper [On the covariance of X in the AX=XB](https://arxiv.org/pdf/1706.03498.pdf).

<p align="center">
  <img src="medias/hand-eye.png" width="200"/>
</p>

The following code snippets shows basic usage of `cope` in finding the covariance of X:

First, import necessary functions
```python
import cope.SE3lib as SE3
import cope.axxbcovariance as axxb
import numpy as np
import pickle
import matplotlib.pyplot as plt
```

Then, input As, Bs and their covariance matrices.
```python
# Read data files
filename = "data/pattern_tfs"
pattern_tfs =  pickle.load(open( filename, "rb" ) )
filename = "data/robot_tfs"
robot_tfs =  pickle.load(open( filename, "rb" ) )
ksamples = 30
# Randomly generate 30 pairs of A and B
datasize = len(pattern_tfs)
alpha = []
beta = []
ta = []
tb = []
for i in range(ksamples):
  # note this
  rand_number_1 = int(np.random.uniform(0,datasize))
  rand_number_2 = int(np.random.uniform(0,datasize))
  while rand_number_1==rand_number_2:
    rand_number_2 = int(np.random.uniform(0,datasize))
  A = np.dot(robot_tfs[rand_number_1],np.linalg.inv(robot_tfs[rand_number_2]))
  B = np.dot(pattern_tfs[rand_number_1],n