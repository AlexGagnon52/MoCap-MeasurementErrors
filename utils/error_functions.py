import ezc3d
import matplotlib.pyplot as plt
import numpy as np
from scipy.interpolate import CubicSpline
from scipy.signal import butter, filtfilt


def load_foot(path: str) -> tuple:
    """Heel and toe markers (mm) and the time (s) of a c3d file.

    Parameters
    ----------
    path : str
        Path to the c3d file.

    Returns
    -------
    tuple
        toe_y, toe_z, heel_y, heel_z, time. y is the walking direction
        and z is the height.
    """
    c3d = ezc3d.c3d(path)
    names = c3d['parameters']['POINT']['LABELS']['value']
    points = c3d['data']['points']          # points[axis, marker, frame]
    toe, heel = names.index('RTOE'), names.index('RHEE')
    time = np.arange(points.shape[2]) / 100     # 100 frames per second
    return (points[1, toe], points[2, toe],
            points[1, heel], points[2, heel], time)


def short_markers(path: str) -> dict:
    """Markers that are valid in only some frames of a c3d file.

    Parameters
    ----------
    path : str
        Path to the c3d file.

    Returns
    -------
    dict
        Marker name and its number of valid frames. A negative residual
        means that the marker was not reconstructed.
    """
    c3d = ezc3d.c3d(path)
    names = c3d['parameters']['POINT']['LABELS']['value']
    residuals = c3d['data']['meta_points']['residuals'][0]
    short = {}
    for i, name in enumerate(names):
        valid = (residuals[i] >= 0).sum()
        if valid < residuals.shape[1]:
            short[name] = valid
    return short


def foot_angle(ty: np.ndarray, tz: np.ndarray,
               hy: np.ndarray, hz: np.ndarray) -> np.ndarray:
    """Angle of the line from the heel marker to the toe marker.

    Parameters
    ----------
    ty, tz, hy, hz : np.ndarray
        Toe (t) and heel (h) y (walking direction) and z (height), in mm.

    Returns
    -------
    np.ndarray
        Foot angle in degrees (0 = flat foot, positive = toes up).
    """
    return np.degrees(np.arctan2(tz - hz, hy - ty))  # walking towards -y


def angle_noise(distance: float, sigma: float) -> float:
    """Angle error (degrees) caused by noise: sqrt(2) * sigma / distance.

    Parameters
    ----------
    distance : float
        Distance between the two markers, in mm.
    sigma : float
        Standard deviation of the noise in each coordinate, in mm.

    Returns
    -------
    float
        Typical angle error in degrees.
    """
    return np.degrees(np.sqrt(2) * sigma / distance)


def add_noise(x: np.ndarray, sigma: float) -> np.ndarray:
    # Add random noise (standard deviation sigma) to every frame.
    return x + np.random.normal(0, sigma, len(x))


def skin_movement(time: np.ndarray, size: float,
                  frequency: float) -> np.ndarray:
    # Smooth up-and-down skin movement (mm) at a frequency (Hz).
    return size * np.sin(2 * np.pi * frequency * time)


def delete_frames(values: np.ndarray, start: int, gap: int) -> np.ndarray:
    # Copy of a curve with `gap` frames deleted (NaN) from `start`.
    gappy = values.copy()
    gappy[start:start + gap] = np.nan
    return gappy


def fill_linear(values: np.ndarray) -> np.ndarray:
    # Fill the gaps (NaN) of a curve with straight lines.
    frames = np.arange(len(values))
    known = ~np.isnan(values)
    return np.interp(frames, frames[known], values[known])


def fill_spline(values: np.ndarray) -> np.ndarray:
    # Fill the gaps (NaN) of a curve with a smooth cubic spline.
    frames = np.arange(len(values))
    known = ~np.isnan(values)
    return CubicSpline(frames[known], values[known])(frames)


def lowpass(values: np.ndarray, cutoff: float,
            rate: float = 100) -> np.ndarray:
    # Low-pass filter (Butterworth, forwards and backwards).
    b, a = butter(4, cutoff / (rate / 2))
    return filtfilt(b, a, values)


def speed_error(new: np.ndarray, true: np.ndarray,
                rate: float = 100) -> float:
    # Average error of the velocity (change per frame time) of a curve.
    speed = np.gradient(new, 1 / rate) - np.gradient(true, 1 / rate)
    return abs(speed).mean()


def largest_error(new: np.ndarray, true: np.ndarray) -> float:
    # Largest absolute difference between two curves.
    return abs(new - true).max()


def average_error(new: np.ndarray, true: np.ndarray) -> float:
    # Average absolute difference between two curves.
    return abs(new - true).mean()


def plot_angles(time: np.ndarray, true_angle: np.ndarray,
                new_angle: np.ndarray) -> None:
    # Plot an angle with an error next to the true angle
    plt.plot(time, new_angle, label='With error')
    plt.plot(time, true_angle, label='True')
    plt.xlabel('Time (s)')
    plt.ylabel('Foot angle (degrees)')
    plt.legend()
    plt.show()


def plot_gap(time: np.ndarray, true: np.ndarray, linear: np.ndarray,
             spline: np.ndarray) -> None:
    # Plot the toe height (mm) with a gap filled in two ways.
    plt.plot(time, true, label='True')
    plt.plot(time, linear, label='Linear')
    plt.plot(time, spline, label='Spline')
    plt.xlabel('Time (s)')
    plt.ylabel('Toe height (mm)')
    plt.legend()
    plt.show()
