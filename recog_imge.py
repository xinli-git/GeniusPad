import tensorflow as tf
import numpy as np
import multiprocessing as mp
import time

from functools import reduce
from copy import deepcopy
import cProfile


def pr_info(*args, mode="I"):
    color_modes = {
        "I": ("INFO"   , "\x1b[1;32m", "\x1b[0m"),
        "W": ("WARNING", "\x1b[1;33m", "\x1b[0m"),
        "E": ("ERROR"  , "\x1b[1;31m", "\x1b[0m")
    }

    print("[{}{:<7}{}] [{:<12}] {}".format(color_modes[mode][1], color_modes[mode][0], color_modes[mode][2],
                                            "APPLICATION", " ".join([str(i) for i in args])))


def debug_img(drawing):
    row, col = drawing.shape

    for i in range(row//10 ):
        for j in range(col//10):
            if drawing[i*10][j*10] > 0:
                print(".", end='')
            else:
                print(" ", end='')
        print()


class RecognitionResult:

    def __init__(self, data=None, info="Not available"):
        self.info = info
        self.data = data

    def run(self):
        pass


class Point:

    def __init__(self, x, y, clusterid = None):
        self.x = x
        self.y = y
        self.clusterid = clusterid
        self.is_noise = True

class Cluster:
    def __init__(self, clusterid, init_point):
        self.id = clusterid
        self.pts = set()
        self.pts.add(init_point)

    def add(self, pt):
        self.pts.add(pt)


def use_subimage_and_predict(cluster):
    x_max = 0
    x_min = 9999999
    y_max = 0
    y_min = 9999999
    for pt in cluster.pts:
        if pt.x > x_max:
            x_max = pt.x
        if pt.x < x_min:
            x_min = pt.x
        if pt.y > y_max:
            y_max = pt.y
        if pt.y < y_min:
            y_min = pt.y

    return x_max, x_min, y_max, y_min


def formulate_result(predictions):
    return RecognitionResult(predictions, "OK")

# this is slow, try to make it faster
def get_only_points(drawing):
    pts = []
    pt_hash = {}
    non_zeros = np.argwhere(drawing>0)
    for i in non_zeros:
        pt = Point(*i)
        pts.append(pt)
        pt_hash[tuple(i)] = pt

    pr_info("Number of Points: ", len(pts))
    return pts, pt_hash
    

def DBSCAN(drawing, eps=5, minpts=10):

    pts, pt_hash = get_only_points(drawing)
    clusters = set()
    cur_cluster = 0

    for pt in pts:
        # point already assigned a cluster
        if pt.clusterid is not None:
            continue
        # find cluster neighbors - the density reachable ones
        neighbors = find_neighbors(drawing, pt, eps, minpts, pt_hash)
        # noise point
        if neighbors is None:
            continue

        cur_cluster += 1
        pt.clusterid = cur_cluster
        new_cluster = Cluster(cur_cluster, pt)
        
        clusters.add(new_cluster)

        # dynamically expand the neighbor space
        for neighbor_pt in neighbors:
            # this neighbor is already identified, don't touch
            if neighbor_pt.clusterid is not None:
                continue
            neighbor_pt.clusterid = cur_cluster
            new_cluster.add(neighbor_pt)

            # search for more density reachable neighbors and append it to the loop list
            new_neighbors = find_neighbors(drawing, neighbor_pt, eps, minpts, pt_hash)
            if new_neighbors is not None:
                neighbors += new_neighbors

    return clusters




def find_neighbors(drawing, pt, eps, minpts, pt_hash):

    ret = []
    row, col  = drawing.shape
    lower_bound = lambda x, e: x - e if x - e > 0 else 0
    upper_bound = lambda x, e, q: x + e + 1 if x + e + 1 < q else q

    upper_x = upper_bound(pt.x, eps, row)
    lower_x = lower_bound(pt.x, eps)

    upper_y = upper_bound(pt.y, eps, col)
    lower_y = lower_bound(pt.y, eps)

    for i in range(lower_x, upper_x):
        for j in range(lower_y, upper_y):
            if drawing[i][j]:
                ret.append(pt_hash[(i,j)])
    if len(ret) < minpts:
        return None
    else:
        return ret


def EquationRecognizer2(img, pipe):
    # make sure we have a queue for inter process communication
    assert(isinstance(pipe, mp.queues.Queue))
    pr_info("received image with shape", img.shape)

    start = time.time()
    clusters = DBSCAN(img)
    end = time.time()
    pr_info("Operation took {:.3f}s, {} clusters".format(end - start, len(clusters)))

    predictions = []
    for each_cluster in clusters:
        predictions.append(use_subimage_and_predict(each_cluster))

    result = formulate_result(predictions)
    pipe.put(result)
    return


def EquationRecognizer(img, pipe):
    cProfile.runctx("EquationRecognizer2(img, pipe)",
                    globals={"EquationRecognizer2": EquationRecognizer2},
                    locals={"img": img, "pipe": pipe} )




#http://www.cse.buffalo.edu/faculty/azhang/cse601/density-based.ppt
# garbage code dump here
'''
    # get points and their pixel location
    pt_iter = np.nditer(drawing, flags=['multi_index', ])
    while not pt_iter.finished:
        if pt_iter[0] == 1:
            pt = Point(*pt_iter.multi_index)
            pts.append(pt)
            pt_hash[pt_iter.multi_index] = pt

        pt_iter.iternext()
    pr_info("Number of Points: ", len(pts))
'''