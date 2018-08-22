import tensorflow as tf
import numpy as np
import os
import gzip
import tensorflow as tf
from tensorflow.python.platform import gfile

DATA = 0
LABEL = 1

# parse error for reading data from file
class DataSetInvalidError(Exception):
    pass

# utility functions for reading and preparing datasets
# ideas taken from tensorflow mnist tutorials
def _read32(bytestream):
  dt = np.dtype(np.uint32).newbyteorder('>')
  return np.frombuffer(bytestream.read(4), dtype=dt)[0]


def get_images(data):

    with gzip.GzipFile(fileobj=data) as bytes:
        magic = _read32(bytes)
        if magic != 2051:
            raise DataSetInvalidError("Wrong magic number")

        items = _read32(bytes)
        rows =  _read32(bytes)
        cols =  _read32(bytes)

        data_bytes =  bytes.read(rows*cols*items)
        image_data = np.frombuffer(data_bytes, dtype=np.uint8)
        image_data = image_data.reshape(items, rows, cols, 1)

        return image_data


def get_labels(data, num_classes=62):

    with gzip.GzipFile(fileobj=data) as bytes:
        magic = _read32(bytes)
        if magic != 2049:
            raise DataSetInvalidError("Wrong magic number")

        items = _read32(bytes)
        data_bytes = bytes.read(items)

        labels = np.frombuffer(data_bytes, dtype=np.uint8)
        with tf.Session() as s:
            one_hot_labels = s.run(tf.one_hot(labels, num_classes))
        return one_hot_labels


def read_data(train, test):

    with gfile.Open(train[DATA], "rb") as data:
        train_data = get_images(data)

    with gfile.Open(train[LABEL], "rb") as label:
        train_label = get_labels(label)

    with gfile.Open(test[DATA], "rb") as data:
        test_data = get_images(data)

    with gfile.Open(test[LABEL], "rb") as label:
        test_label = get_labels(label)


    return (train_data, train_label), (test_data, test_label)


#returns a generator that produces data of size batch_size
def data_generator(data, batch_size=500):

    pass


# cnn layers to construct the network
def weight_variable(shape):
    initial = tf.truncated_normal(shape, stddev=0.1)
    return tf.Variable(initial)


def bias_variable(shape):
    initial = tf.constant(0.1, shape=shape)
    return tf.Variable(initial)


def conv2d(x, W):
    return tf.nn.conv2d(x, W, strides=[1, 1, 1, 1], padding='SAME')


def max_pool_2x2(x):
    return tf.nn.max_pool(x, ksize=[1, 2, 2, 1],
                          strides=[1, 2, 2, 1], padding='SAME')


def train(x_from_the_other_side):
        os.environ["CUDA_VISIBLE_DEVICES"] = "0"
        # sicne our images are made to the same format as mnist, use mnist functions to import data

        train_data_path = [os.path.join(os.getcwd(), "AlphaNumericData", f) for f in
                 ("emnist-balanced-train-images-idx3-ubyte.gz",
                  "emnist-balanced-train-labels-idx1-ubyte.gz")]

        test_data_path = [os.path.join(os.getcwd(), "AlphaNumericData", f) for f in
                 ("emnist-balanced-test-images-idx3-ubyte.gz",
                  "emnist-balanced-test-labels-idx1-ubyte.gz")]

        train, test = read_data(train_data_path, test_data_path)

        train_data = data_generator(train[DATA])
        test_data =  data_generator(test[DATA])

        x = tf.placeholder(tf.float32, [None, 784])

        W_conv1 = weight_variable([5, 5, 1, 32])
        b_conv1 = bias_variable([32])

        x_image = tf.reshape(x, [-1, 28, 28, 1])

        h_conv1 = tf.nn.relu(conv2d(x_image, W_conv1) + b_conv1)
        h_pool1 = max_pool_2x2(h_conv1)

        W_conv2 = weight_variable([5, 5, 32, 64])
        b_conv2 = bias_variable([64])

        h_conv2 = tf.nn.relu(conv2d(h_pool1, W_conv2) + b_conv2)
        h_pool2 = max_pool_2x2(h_conv2)

        W_fc1 = weight_variable([7 * 7 * 64, 1024])
        b_fc1 = bias_variable([1024])

        h_pool2_flat = tf.reshape(h_pool2, [-1, 7 * 7 * 64])
        h_fc1 = tf.nn.relu(tf.matmul(h_pool2_flat, W_fc1) + b_fc1)

        keep_prob = tf.placeholder(tf.float32)
        h_fc1_drop = tf.nn.dropout(h_fc1, keep_prob)

        W_fc2 = weight_variable([1024, 10])
        b_fc2 = bias_variable([10])

        y_conv = tf.nn.softmax(tf.matmul(h_fc1_drop, W_fc2) + b_fc2)

        y_ = tf.placeholder(tf.float32, [None, 10])

        cross_entropy = tf.reduce_mean(-tf.reduce_sum(y_ * tf.log(y_conv), reduction_indices=[1]))

        train_step = tf.train.AdamOptimizer(1e-4).minimize(cross_entropy)

        answer = tf.argmax(y_conv, 1)
        correct_prediction = tf.equal(tf.argmax(y_conv, 1), tf.argmax(y_, 1))
        accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

        init = tf.initialize_all_variables()

        sess = tf.Session()
        sess.run(init)

        for i in range(2000):

            batch_xs, batch_ys = next(train_data)
            if i % 100 == 0:
                train_accuracy = accuracy.eval(session=sess, feed_dict={x: batch_xs, y_: batch_ys, keep_prob: 1.0})
                print("step %d, training accuracy %.3f" % (i, train_accuracy))
            sess.run(train_step, feed_dict={x: batch_xs, y_: batch_ys, keep_prob: 0.5})


        print("answer is:", answer.eval(session=sess,
                                                 feed_dict={x: x_from_the_other_side, keep_prob: 0.5}))

if __name__ == "__main__":
    train(1)