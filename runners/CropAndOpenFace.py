"""
.. module CropAndOpenFace
    :synopsis: Contains a method for running OpenFace on a video directory as well as a class which crops a video and
    runs OpenFace on it
"""

import glob
import json
import os
import subprocess
import sys
from dask import dataframe as df
import pandas as pd
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import ImageCropper
import VidCropper


def run_open_face(im_dir, vid_mode=False, remove_intermediates=False) -> str:
    """
    Runs OpenFace

    :param im_dir: Location of images if not in video mode, location of video if in video mode
    :param vid_mode: Whether or not to be in video mode (alternative is to run on an image sequence)
    :param remove_intermediates: Whether or not to remove intermediate files
    :return: Name of output video produced by OpenFace (with landmarks)
    """
    executable = '/home/gvelchuru/OpenFace/build/bin/FeatureExtraction'  # Change to location of OpenFace

    if not vid_mode:
        subprocess.Popen(
            "ffmpeg -y -r 30 -f image2 -pattern_type glob -i '{0}' -b:v 7000k {1}"
            .format(
                os.path.join(im_dir, '*.png'),
                os.path.join(im_dir, 'inter_out.mp4')),
            shell=True).wait()
        vid_name = 'inter_out.mp4'
        out_name = 'out.mp4'
    else:
        vid_name = 'inter_out.avi'
        out_name = 'out.avi'

    FNULL = open(os.devnull, 'w')
    subprocess.Popen(
        '{0} -f {1} -of {2} -ov {3} -q -wild -multi-view 1'.format(
            executable, os.path.join(im_dir, vid_name),
            os.path.join(im_dir, 'au.csv'), os.path.join(im_dir, out_name)),
        shell=True,
        stdout=FNULL,
        stderr=subprocess.STDOUT).wait()

    vid_name = os.path.basename(im_dir).replace('_cropped', '')
    vid_name_parts = vid_name.split('_')
    patient_name = vid_name_parts[0]
    day_num = vid_name_parts[1]
    session_num = vid_name_parts[2]

    if 'au.csv' in os.listdir(im_dir):
        au_dataframe = df.read_csv(os.path.join(im_dir, 'au.csv'))
        # sLength = len(au_dataframe['frame'])
        au_dataframe = au_dataframe.assign(patient=lambda x: patient_name)
        au_dataframe = au_dataframe.assign(day=lambda x: day_num)
        au_dataframe = au_dataframe.assign(session=lambda x: session_num)
        au_dataframe = au_dataframe.compute()
        # au_dataframe = au_dataframe.assign(
        df_dir = os.path.join(im_dir, 'hdfs')

        if not os.path.exists(df_dir):
            os.mkdir(df_dir)
        au_dataframe.to_hdf(os.path.join(df_dir, 'au_0.hdf'), '/data', format='table')
        # df.read_hdf(os.path.join(df_dir, 'au_0.hdf'), '/data') # assert saved correctly

    if remove_intermediates:
        os.remove(os.path.join(im_dir, vid_name))

    return out_name


class VideoImageCropper:
    def __init__(self,
                 vid=None,
                 im_dir=None,
                 already_cropped=None,
                 already_detected=None,
                 crop_txt_files=None,
                 nose_txt_files=None,
                 vid_mode=False):
        self.already_cropped = already_cropped
        self.already_detected = already_detected
        self.im_dir = im_dir

        if not self.already_cropped and not self.already_detected:
            if crop_txt_files:
                self.crop_txt_files = crop_txt_files
            else:
                try:
                    self.crop_txt_files = json.load(
                        open(
                            os.path.join(
                                os.path.dirname(vid), 'crop_files_list.txt'),
                            mode='r'))
                except IOError:
                    self.crop_txt_files = find_txt_files(crop_path)

            if nose_txt_files:
                self.nose_txt_files = nose_txt_files
            else:
                try:
                    self.nose_txt_files = json.load(
                        open(
                            os.path.join(
                                os.path.dirname(vid), 'nose_files_list.txt'),
                            mode='r'))
                except IOError:
                    self.nose_txt_files = find_txt_files(nose_path)

            if not os.path.lexists(self.im_dir):
                os.mkdir(self.im_dir)

        if not vid_mode:
            subprocess.Popen(
                'ffmpeg -y -i "{0}" -vf fps=30 "{1}"'.format(
                    vid,
                    os.path.join(self.im_dir,
                                 (os.path.basename(vid) + '_out%04d.png'))),
                shell=True).wait()
            ImageCropper.CropImages(
                self.im_dir,
                self.crop_txt_files,
                self.nose_txt_files,
                save=True)

            if len(glob.glob(os.path.join(self.im_dir, '*.png'))) > 0:
                if not self.already_detected:
                    run_open_face(self.im_dir)
        else:
            VidCropper.CropVid(vid, self.im_dir, self.crop_txt_files,
                               self.nose_txt_files)
            run_open_face(self.im_dir, vid_mode=True)


def find_txt_files(path):
    return {
        os.path.splitext(os.path.basename(v))[0]: v

        for v in glob.iglob(os.path.join(path + '/**/*.txt'), recursive=True)
    }


if __name__ == '__main__':
    vid = None

    if '-v' in sys.argv:
        vid = sys.argv[sys.argv.index('-v') + 1]
    crop_path = sys.argv[sys.argv.index('-c') + 1]
    nose_path = sys.argv[sys.argv.index('-n') + 1]
    already_cropped = ('-ac' in sys.argv)
    already_detected = ('-ad' in sys.argv)

    if '-id' in sys.argv:
        im_dir = sys.argv[sys.argv.index('-id') + 1]
    else:
        im_dir = os.path.splitext(vid)[0] + '_cropped'
    crop = VideoImageCropper(
        vid,
        im_dir,
        crop_path,
        nose_path,
        already_cropped,
        already_detected,
        vid_mode=True)
