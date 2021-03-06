"""
.. module MultiCropAndOpenFace
    :synopsis: Script to apply cropping and OpenFace to all videos in a directory.

"""

import glob
import json
import os
import subprocess
import sys
import numpy as np
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import CropAndOpenFace


def make_vids(path, all = False):
    """
    Return list of vids not processed yet given a path
    :param path: Path to video directory
    :type path: str
    :return: list of vids to do
    """
    folder_components = set(os.path.join(path, x) for x in os.listdir(path))

    return [
        x for x in glob.glob(os.path.join(path, '*.avi'))

        if (os.path.splitext(x)[0] + '_cropped' not in folder_components
            or 'hdfs' not in os.listdir(
                os.path.join(path,
                             os.path.splitext(x)[0] + '_cropped')))
    ]


def make_crop_and_nose_files(path):
    crop_file = os.path.join(path, 'crop_files_list.txt')
    nose_file = os.path.join(path, 'nose_files_list.txt')

    if not os.path.exists(crop_file):
        crop_path = sys.argv[sys.argv.index('-c') + 1]
        crop_txt_files = CropAndOpenFace.find_txt_files(crop_path)
        json.dump(crop_txt_files, open(crop_file, mode='w'))

    if not os.path.exists(nose_file):
        nose_path = sys.argv[sys.argv.index('-n') + 1]
        nose_txt_files = CropAndOpenFace.find_txt_files(nose_path)
        json.dump(nose_txt_files, open(nose_file, mode='w'))

    return json.load(open(crop_file)), json.load(open(nose_file))


if __name__ == '__main__':

    path = sys.argv[sys.argv.index('-id') + 1]

    vids = make_vids(path)
    num_GPUs = 1
    processes = []
    indices = np.linspace(0, len(vids), num=num_GPUs + 1)

    # TODO: make this a cmd-line arg
    CONDA_ENV = '/home/gvelchuru/miniconda3/envs/OpenFace/bin/python'

    for index in range(len(indices) - 1):
        if '-c' not in sys.argv:
            cmd = [
                CONDA_ENV,
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'helpers', 'HalfCropper.py'), '-id', path, '-vl',
                str(int(indices[index])), '-vr',
                str(int(indices[index + 1]))
            ]
        else:
            cmd = [
                CONDA_ENV,
                os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    'helpers', 'HalfCropper.py'), '-id', path, '-vl',
                str(int(indices[index])), '-vr',
                str(int(indices[index + 1])), '-c', sys.argv[sys.argv.index('-c') + 1], '-n', sys.argv[sys.argv.index('-n') + 1]
            ]
        processes.append(
            subprocess.Popen(
                cmd, env={'CUDA_VISIBLE_DEVICES': '{0}'.format(str(index))}))

    [p.wait() for p in processes]
