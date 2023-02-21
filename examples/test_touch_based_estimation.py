import trimesh
import numpy as np
import cope.SE3lib as SE3
import cope.particlelib as ptcl
import pickle

extents    = [0.05,0.1,0.2]
mesh       = trimesh.creation.box(extents)
pkl_file   = open('data/woodstick_w_dict.p', 'rb')
angle_dict = pickle.load(pkl_file)
pkl_file.close()

measurements = [[np.array([-0.02882446, -0.04892219,  0.00738576]),
                 np.array([-0.40190523, -0.90828342, -0.11616118])],
                [np.array([ 0.01610016,  0.04007391,  0.01259628]),
                 np.array([ 0.52140577,  0.83554119,  0.17322511])],
                # [np.array([ -1.470e-05,  2.2329e-02,  8.2384e-02]),
                #  np.array([-0.88742601,  0.40497962,  0.22015128])],
                [np.array([-0.00351179, -0.0564559