#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017 Huy Nguyen <huy.nguyendinh09@gmail.com>
#
# This file is part of python-cope.
#
# python-cope is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# python-cope is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# python-cope. If not, see <http://www.gnu.org/licenses/>.

import numpy  as np
import trimesh
import scipy as sp
from scipy.stats import norm
import cope.SE3lib as SE3
import bisect
import cope.transformation as tr
import random
import time
import copy
import matplotlib.pyplot as plt


class Region(object):
  def __init__(self, particles, delta_rot,delta_trans):
    self.particles = particles #List of particles (transformations)
    self.delta_rot = delta_rot
    self.delta_trans = delta_trans

def IsInside(point,center,radius):
  if np.linalg.norm(point-center) < radius:
    return True
  return False


def EvenDensityCover(region, M):
  '''Input: Region V_n - sampling region represented as a union of neighborhoods, M - number of particles to sample per neighborhood
  Output: a set of particles that evenly cover the region (the new spheres will have analogous shape to the region sigma)
  '''
  particles = []
  num_spheres = len(region.particles)
  delta_rot = region.delta_rot
  delta_trans = region.delta_trans
  for i  in range(num_spheres):
    center_particle = region.particles[i]
    center_vec_rot =  SE3.RotToVec(center_particle[:3,:3])
    center_vec_trans = center_particle[:3,3]
    num_existing = 0
    for p in particles:
      if IsInside(SE3.RotToVec(p[:3,:3]),center_vec_rot,delta_rot) and IsInside(p[:3,3],center_vec_trans,delta_trans):
        num_existing += 1
    for m in range(M-num_existing):
      count = 0
      accepted = False
      while not accepted and count < 5:
        new_vec_rot = np.random.uniform(-1,1,size = 3)*delta_rot + center_vec_rot
        new_vec_trans = np.random.uniform(-1,1,size = 3)*delta_trans + center_vec_trans
        count += 1
        accepted = True
        for k in range(i-1):
          previous_center = region.particles[k]
          previous_vec_rot = SE3.RotToVec(previous_center[:3,:3])
          previous_vec_trans = previous_center[:3,3]
          if IsInside(SE3.RotToVec(p[:3,:3]),previous_vec_rot,delta_rot) and IsInside(p[:3,3],previous_vec_trans,delta_trans):
            accepted = False
            break
      if accepted:
        new_p = np.eye(4)
        new_p[:3,:3] = SE3.VecToRot(new_vec_rot)
        new_p[:3,3] = new_vec_trans
        particles.append(new_p)
  return particles

def normalize(weights):
  norm_weights = np.zeros(len(weights))
  sum_weights = np.sum(weights)
  if sum_weights == 0:
    return np.ones(len(weights))/len(weights)
  for i in range(len(weights)):
    norm_weights[i] = weights[i]/sum_weights
  return norm_weights

def ComputeNormalizedWeightsB(mesh,sorted_face,particles,measurements,pos_err,nor_err,tau):
  num_particles = len(particles)
  new_weights = np.zeros(num_particles)
  for i in range(len(particles)):
    T = np.linalg.inv(particles[i])
    D = copy.deepcopy(measurements)
    for d in D:
      d[0] = np.dot(T[:3,:3],d[0]) + T[:3,3]
      d[1] = np.dot(T[:3,:3],d[1])
    total_energy = sum([FindminimumDistanceMeshOriginal(mesh,sorted_face,measurement,pos_err,nor_err)**2 for measurement in D])
    new_weights[i] = (np.exp(-0.5*total_energy/tau))
  return normalize(new_weights)

def ComputeNormalizedWeights(mesh,sorted_face,particles,measurements,pos_err,nor_err,tau):
  num_particles = len(particles)
  new_weights = np.zeros(num_particles)
  for i in range(len(particles)):
    T = np.linalg.inv(particles[i])
    D = copy.deepcopy(measurements)
    for d in D:
      d[0] = np.dot(T[:3,:3],d[0]) + T[:3,3]
      d[1] = np.dot(T[:3,:3],d[1])
    total_energy = sum([FindminimumDistanceMesh(mesh,sorted_face,measurement,pos_err,nor_err)**2 for measurement in D])
    new_weights[i] = (np.exp(-0.5*total_energy/tau))
  
  return normalize(new_weights)


def FindminimumDistanceMesh(mesh,sorted_face,measurement,pos_err,nor_err):
    ref_vec = sorted_face[2]
    sorted_angle = sorted_face[1]
    face_idx = sorted_face[0]
    angle =  np.arccos(np.dot(measurement[1],ref_vec))
    idx = bisect.bisect_right(sorted_angle,angle)
    if idx >= len(sorted_angle):
      up_bound = idx
    else:
      up_bound = idx + bisect.bisect_right(sorted_angle[idx:],sorted_angle[idx]+sorted_angle[idx]-angle+nor_err)
    if idx == 0:
      low_bound = 0
    else:
      low_bound = bisect.bisect_left(sorted_angle[:idx],sorted_angle[idx-1]-(sorted_angle[idx-1]-angle)-nor_err)-1
    dist = []
    for i in range(low_bound,up_bound):
        A,B,C = mesh.faces[face_idx[i]]
        dist.append(CalculateDistanceFace([mesh.vertices[A],mesh.vertices[B],mesh.vertices[C],mesh.face_normals[face_idx[i]]],measurement,pos_err,nor_err))
    return min(dist)

def FindminimumDistanceMeshOriginal(mesh,sorted_face,measurement,pos_err,nor_err):
    dist = []
    for i in range(len(mesh.faces)):
        A,B,C = mesh.faces[i]
        dist.append(CalculateDistanceFace([mesh.vertices[A],mesh.vertices[B],mesh.vertices[C],mesh.face_normals[i]],measurement,pos_err,nor_err))
    return min(dist)

def CalculateDistanceFace(face,measurement,pos_err,nor_err):
    p1,p2,p3,nor = face
    pos_measurement = measurement[0]
    nor_measurement = measurement[1]
    norm = lambda x: np.linalg.norm(x)
    inner = lambda a, b: np.inner(a,b)
    closest_point = trimesh.triangles.closest_point([[p1,p2,p3]],[pos_measurement])
    diff_distance = norm(closest_point-pos_measurement)
    diff_angle    = np.arccos(inner(nor, nor_measurement)/norm(nor)/norm(nor_measurement))
    dist = np.sqrt(diff_distance**2/pos_err**2+diff_angle**2/nor_err**2)
    return dist

def CalculateMahaDistanceFace(face,measurement,pos_err,nor_err):
  p1,p2,p3,nor = face
  pos_measurement = measurement[0]
  nor_measurement = measurement[1]
  norm = lambda x: np.linalg.norm(x)
  inner = lambda a, b: np.inner(a,b)
  diff_distance   = norm(inner((pos_measurement-p1), nor)/norm(nor))
  diff_angle      = np.arccos(inner(nor, nor_measurement)/norm(nor)/norm(nor_measurement))
  dist = np.sqrt(diff_distance**2/pos_err**2+diff_angle**2/nor_err**2)
  return dist


def Pruning(list_particles, weights,percentage):
  assert (len(list_particles)==len(weights)),"Wrong input data, length of list of particles are not equal to length of weight"
  num_particles = len(list_particles)
  pruned_list = []
  new_list_p = []
  new_list_w = []
  c = np.zeros(num_particles)
  c[0] = weights[0]
  for i in range(num_particles-1):
    c[i+1] = c[i] + weights[i+1]
  u = np.zeros(num_particles)
  u[0] = np.random.uniform(0,1)/num_particles
  k = 0
  for i in range(num_particles):
    u[i] = u[0] + 1./num_particles*i
    while (u[i] > c[k]):
      k+=1
    new_list_p.append(list_particles[k]) 
  for i in range(num_particles):
    if i == 0:
      pruned_list.append(new_list_p[i])
    else:
      if not np.allclose(np.dot(new_list_p[i],np.linalg.inv(new_list_p[i-1])),np.eye(4)):
        # IPython.embed()
        pruned_list.append(new_list_p[i])
  return pruned_list
      

def Pruning_old(list_particles, weights,prune_percentage):
  assert (len(list_particles)==len(weights)),"Wrong input data, length of list of particles are not equal to length of weight"
  pruned_list = []
  maxweight = 0
  for w in weights:
    if w > maxweight:
      maxweight = w
  threshold = prune_percentage*maxweight
  for i in range(len(list_particles)):
    if weights[i] > threshold:
      pruned_list.append(list_particles[i])
  return pruned_list

def Visualize(mesh,particle,D=[]):
  show_ = mesh.copy()
  show_.apply_transform(particle)
  color = np.array([  21, 51,  252, 255])
  for face in show_.faces:
    show_.visual.face_colors[face] = color
  for facet in show_.facets:
    show_.visual.face_colors[facet] = color
  for d in D:
    sphere = trimesh.creation.icosphere(3,0.0025)
    TF = np.eye(4)
    TF[:3,3] = d[0]
    TF2 = np.eye(4)
    angle = np.arccos(np.dot(d[1],np.array([0,0,1])))
    vec = np.cross(d[1],np.array([0,0,1]))
    TF2[:3,:3] = SE3.VecToRot(angle*vec)
    TF2[:3,3] = d[0] + np.dot(SE3.VecToRot(angle*vec),np.array([0,0,0.1/2.]))
    sphere.apply_transform(TF)
    show_ += sphere
  show_.show()
  return True

def Volume(radius,dim):
  return (np.pi**(dim/2.))/sp.special.gamma(dim/2.+1)*(radius**dim)


def ScalingSeriesB(mesh,sorted_face, particles0, measurements, pos_err, nor_err, M, sigma0, sigma_desired, prune_percentage = 0.6,dim = 6, visualize = False):
  """
  @type  V0:  ParticleFilterLib.Region
  @param V0:  initial uncertainty region
  @param  D:  a list of measurements [p,n,o_n,o_p] p is the contacted point, n is the approaching vector (opposite to normal)
  @param  M:  the no. of particles per neighborhood
  @param delta_desired: terminal value of delta
  @param dim: dimension of the state space (6 DOFs)
  """ 
  zoom = 2**(-1./6.)
  delta_rot = np.max(np.linalg.cholesky(sigma0[3:,3:]).T)
  delta_trans = np.max(np.linalg.cholesky(sigma0[:3,:3]).T)
  delta_desired_rot = np.max(np.linalg.cholesky(sigma_desired[3:,3:]).T)
  delta_desired_trans = np.max(np.linalg.cholesky(sigma_desired[:3,:3]).T)
  N_rot  = np.log2(Volume(delta_rot,3)/Volume(delta_desired_rot,3))
  N_trans = np.log2(Volume(delta_trans,3)/Volume(delta_desired_trans,3))
  N = int(np.round(max(N_rot,N_trans)))
  particles = particles0
  V = Region(particles,delta_rot,delta_trans)
  t1 = 0.
  t2 = 0.
  t3 = 0.
  sum_num_particles = 0
  for n in range(N):
    delta_rot = delta_rot*zoom
    delta_trans = delta_trans*zoom
    tau = (delta_trans/delta_desired_trans)**(2./1.)
    # Sample new set of particles based on from previous region and M
    particles = EvenDensityCover(V,M)
    # print "len of new generated particles ", len(particles)
    # print 'tau ', tau
    # Compute normalized weights
    weights = ComputeNormalizedWeightsB(mesh,sorted_face,particles,measurements,pos_err,nor_err,tau)
    # Prune based on weights
    pruned_particles = Pruning_old(particles,weights,prune_percentage)
    # print 'No. of particles, after pruning:', len(pruned_particles)
    # Create a new region from the set of particle left after pruning
    V = Region(pruned_particles,delta_rot,delta_trans)
    # if visualize:
    #   Visualize(visualize_mesh,particles,measurements)
    sum_num_particles += len(particles)
  new_set_of_particles = EvenDensityCover(V,M)
  new_weights = ComputeNormalizedWeightsB(mesh,sorted_face,new_set_of_particles,measurements,pos_err,nor_err,1)
  return new_set_of_particles, new_weights

def ScalingSeries(mesh,sorted_face, particles0, measurements, pos_err, nor_err, M, sigma0, sigma_desired, prune_percentage = 0.6,dim = 6, visualize = False):
  """
  @type  V0:  ParticleFilterLib.Region
  @param V0:  initial uncertainty region
  @param  D:  a list of measurements [p,n,o_n,o_p] p is the contacted point, n is the approaching vector (opposite to normal)
  @param  M:  the no. of particles per neighborhood
  @param delta_desired: terminal value of delta
  @param dim: dimension of the state space (6 DOFs)
  """ 
  zoom = 2**(-1./6.)
  delta_rot = np.max(np.linalg.cholesky(sigma0[3:,3:]).T)
  delta_trans = np.max(np.linalg.cholesky(sigma0[:3,:3]).T)
  delta_desired_rot = np.max(np.linalg.cholesky(sigma_desired[3:,3:]).T)
  delta_desired_trans = np.max(np.linalg.cholesky(sigma_desired[:3,:3]).T)
  N_rot  = np.log2(Volume(delta_rot,3)/Volume(delta_desired_rot,3))
  N_trans = np.log2(Volume(delta_trans,3)/Volume(delta_desired_trans,3))
  N = int(np.round(max(N_rot,N_trans)))
  particles = particles0
  V = Region(particles,delta_rot,delta_trans)
  for n in range(N):
    delta_rot = delta_rot*zoom
    delta_trans = delta_trans*zoom
    tau = (delta_trans/delta_desired_trans)**(2./1.)  
    # Sample new set of particles based on from previous region and M
    particles = EvenDensityCover(V,M)
    # print "len of new generated particles ", len(particles)
    # print 'tau ', tau
    # Compute normalized weights
    weights = ComputeNormalizedWeights(mesh,sorted_face,particles,measurements,pos_err,nor_err,tau)
    # Prune based on weights
    pruned_particles = Pruning_old(particles,weights,prune_percentage)     
    # print 'No. of particles, after pruning:', len(pruned_particles)
    # Create a new region from the set of particle left after pruning
    V = Region(pruned_particles,delta_rot,delta_trans)
    # if visualize:
    #   Visualize(mesh,particles,measurements)
  new_set_of_particles =  EvenDensityCover(V,M)
  new_weights = ComputeNormalizedWeights(mesh,sorted_face,new_set_of_particles,measurements,pos_err,nor_err,1)
  return new_set_of_particles, new_weights


def GenerateMeasurementsTriangleSampling(mesh,pos_err,nor_err,num_measurements):
  ## Generate random points on obj surfaces using triangle sampling
  # For individual triangle sampling uses this method:
  # http://mathworld.wolfram.com/TrianglePointPicking.html
  # # len(mesh.faces) float array of the areas of each face of the mesh
  # area = mesh.area_faces
  # # total area (float)
  # area_sum = np.sum(area)
  # # cumulative area (len(mesh.faces))
  # area_cum = np.cumsum(area)
  # face_pick = np.random.random(num_measurements)*area_sum
  # face_index = np.searchsorted(area_cum, face_pick)

  face_w_normal_up = []
  for i in range(len(mes