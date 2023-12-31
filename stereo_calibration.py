import os
import shutil
import argparse
import numpy as np

from Camera import Camera
from config import CalibrationConfig, ReconstructionsConfig, CameraConfig
from Calibration import stereo_camera_calibration, save_json, read_json

from multiprocessing import Process, Barrier

parser = argparse.ArgumentParser(description="Test file")
parser.add_argument("-so", "--stream-off", dest="stream",
                    type=bool, default=True, const=False, nargs="?", help="Using the camera (default True)")

arguments = parser.parse_args()

if arguments.stream:
    try:
        shutil.rmtree(CalibrationConfig.stereo_calibration_path)
    except FileNotFoundError:
        pass

    try:
        os.mkdir(CalibrationConfig.stereo_calibration_path)
        os.mkdir(ReconstructionsConfig.inside_camera_parameters_path)
    except FileExistsError:
        pass


def main():

    barrier = Barrier(len(CameraConfig.ids))

    process = []

    for camera_id in CameraConfig.ids:

        if arguments.stream:
            camera = Camera(device_id=camera_id,
                            mode="frame",
                            width=CameraConfig.width,
                            height=CameraConfig.height)

            kwargs_cameras = {
                "img_count": CalibrationConfig.img_count,
                "time_out": CalibrationConfig.time_out,
                "path": CalibrationConfig.stereo_calibration_path,
                "show_gui": CalibrationConfig.show_gui,
                "barrier": barrier,
            }

            mp_process = Process(target=camera.stream, kwargs=kwargs_cameras, name=f"Camera_{camera_id}")
            process.append(mp_process)

            mp_process.start()

    if arguments.stream:
        process[0].join()

    inside_camera_params_left = read_json(f"{ReconstructionsConfig.inside_camera_parameters_path}/camera_{CameraConfig.ids[0]}.json")
    inside_camera_params_right = read_json(f"{ReconstructionsConfig.inside_camera_parameters_path}/camera_{CameraConfig.ids[1]}.json")

    R, T = stereo_camera_calibration(matrix1=np.array(inside_camera_params_left["matrix"]),
                                     matrix2=np.array(inside_camera_params_right["matrix"]),
                                     dist1=np.array(inside_camera_params_left["dist"]),
                                     dist2=np.array(inside_camera_params_right["dist"]),
                                     frames_folder1=f"{CalibrationConfig.stereo_calibration_path}/Camera_{CameraConfig.ids[0]}_frame",
                                     frames_folder2=f"{CalibrationConfig.stereo_calibration_path}/Camera_{CameraConfig.ids[1]}_frame",
                                     save=CalibrationConfig.save)

    inside_stereo_params = {
        "camera_left": {
            "RMSE": inside_camera_params_left["RMSE"],
            "matrix": inside_camera_params_left["matrix"],
            "dist": inside_camera_params_left["dist"],
            "rotVecs": inside_camera_params_left["rotVecs"],
            "tvecs": inside_camera_params_left["tvecs"]
        },

        "camera_right": {
            "RMSE": inside_camera_params_right["RMSE"],
            "matrix": inside_camera_params_right["matrix"],
            "dist": inside_camera_params_right["dist"],
            "rotVecs": inside_camera_params_right["rotVecs"],
            "tvecs": inside_camera_params_right["tvecs"]
        },

        "R": R.tolist(),
        "T": T.tolist()

    }

    save_json(data=inside_stereo_params,
              path=ReconstructionsConfig.inside_camera_parameters_path,
              name_file=f"stereo_params")


if __name__ == "__main__":
    main()