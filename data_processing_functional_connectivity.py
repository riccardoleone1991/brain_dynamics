"""
Function for data pre-processing to get dynamic function connectivity 
multidimensional matrix.
Takes data as a numpy array and performs a PCA 
and then compares by cosine similarity all time points to return a phase-lag 
matrix of dynamic functional connectivity.

Katerina Capouskova 2018, kcapouskova@hotmail.com
"""

import json
import os

import numpy as np
import pylab
from numpy.linalg import linalg
from scipy import signal
from sklearn import manifold, preprocessing
from sklearn.decomposition import PCA
from tqdm import tqdm

from utilities import return_paths_list, create_dir, find_delimeter


def convert_to_phases(input_path, output_path, brain_areas, t_phases, subject, TR):
    """
    Converts BOLD signal into phases by Hilbert Transform with filtering included.

    :param input_path: path to input file
    :type input_path: str
    :param output_path: path to output directory
    :type output_path: str
    :param brain_areas: number of brain areas
    :type brain_areas: int
    :param t_phases: number of time phases
    :type t_phases: int
    :param subject: subject number
    :type subject: int
    :param TR: repetition time
    :type TR: int
    :return: phases matrix
    :rtype: np.ndarray
    """


    phases = np.full((brain_areas, t_phases), fill_value=0).astype(np.float64)
    delim = find_delimeter(input_path)
    array = np.genfromtxt(input_path, delimiter=delim)
    for area in tqdm(range(0, brain_areas)):
        # # select by columns, transform to phase
        # The data I use is already detrended and demeaned
        # time_series = demean(signal.detrend(array[:, area]))
        # filtered_ts = filter_signal(time_series, TR)
        phases[area, :] = np.angle(signal.hilbert(array[:, area]))
    np.savez_compressed(os.path.join(output_path, 'phases_{}'.format(subject)), phases)
    return phases


def filter_signal(time_series, TR):
    """
    Performs bandpass filtering of BOLD signal data.

    :param time_series: time series array
    :type time_series: np.ndarray
    :param TR: repetition time
    :type TR: int
    :return: filtered time series
    :rtype: np.ndarray
    """
    # Nyquist
    nyq = 1.0 / (2.0 * TR)
    # Lowpass frequency of filter (Hz)
    low = 0.04 / nyq
    # Highpass frequency of filter (Hz)
    high = 0.07 / nyq
    Wn = [low, high]
    # 2nd order butterworth filter
    k = 2
    # Constructing the filter
    b, a = signal.butter(k, Wn, btype='band', output='ba')
    # Filtering
    filt_ts = signal.lfilter(b, a, time_series)
    return filt_ts


def dynamic_functional_connectivity(paths, output_path, brain_areas,
                                    pattern, t_phases, n_subjects, TR):
    """
    Computes the dynamic functional connectivity of brain areas.

    :param paths: list of paths in input dir
    :type paths: []
    :param output_path: path to output directory
    :type output_path: str
    :param brain_areas: number of brain areas
    :type brain_areas: int
    :param pattern: pattern of input files
    :type pattern: str
    :param t_phases: number of time points
    :type t_phases: int
    :param n_subjects: number of subjects
    :type n_subjects:int
    :param TR: repetition time
    :type TR: int
    :return: dFC output path
    :rtype: str
    """
    dFC = np.full((brain_areas, brain_areas), fill_value=0).astype(np.float64)

    for n in tqdm(range(n_subjects)):
        phases = convert_to_phases(paths[n], output_path, brain_areas, t_phases, n, TR)
        for t in range(0, t_phases):
            for i in range(0, brain_areas):
                for z in range(0, brain_areas):
                    if np.absolute(phases[i, t] - phases[z, t]) > np.pi:
                        dFC[i, z] = np.cos(2 * np.pi - np.absolute(
                            phases[i, t] - phases[z, t]))
                    else:
                        dFC[i, z] = np.cos(np.absolute(phases[i, t] -
                                                       phases[z, t]))
            dfc_output = os.path.join(output_path, 'dFC')
            create_dir(dfc_output)
            np.savez_compressed(os.path.join(dfc_output, 'subject_{}_time_{}'.format(n, t)), dFC)

    return dfc_output


def preform_pca_on_dynamic_connectivity(paths, output_path, brain_areas,
                                        pattern, t_phases, n_subjects, TR):
    """
    Computes the dynamic connectivity of brain areas with performing
    a PCA returning its matrix.

    :param paths: list of paths in input dir
    :type paths: []
    :param output_path: path to output directory 
    :type output_path: str
    :param brain_areas: number of brain areas
    :type brain_areas: int
    :param pattern: pattern of input files
    :type pattern: str
    :param t_phases: number of time points
    :type t_phases: int
    :param n_subjects: number of subjects
    :type n_subjects:int
    :param TR: repetition time
    :type TR: int
    :return: PCA matrix, PCA matrix shape
    :rtype: np.ndarray, tuple
    """
    dFC = np.full((brain_areas, brain_areas), fill_value=0).astype(np.float64)
    pca_components = np.full((n_subjects, t_phases, (brain_areas * 2)),
                             fill_value=0).astype(np.float64)
    for n in tqdm(range(n_subjects)):
        phases = convert_to_phases(paths[n], output_path, brain_areas, t_phases, n, TR)
        for t in range(0, t_phases):
            for i in range(0, brain_areas):
                for z in range(0, brain_areas):
                    if np.absolute(phases[i, t] - phases[z, t]) > np.pi:
                        dFC[i, z] = np.cos(2 * np.pi - np.absolute(
                            phases[i, t] - phases[z, t]))
                    else:
                        dFC[i, z] = np.cos(np.absolute(phases[i, t] -
                                                       phases[z, t]))
            dfc_output = os.path.join(output_path, 'dFC')
            create_dir(dfc_output)
            np.savez(os.path.join(dfc_output, 'subject_{}_time_{}'.format(n, t)), dFC)
            pca = PCA(n_components=2)
            # normalize
            # dFC = preprocessing.normalize(dFC, norm='l2')
            pca.fit(dFC)
            pca_dict = {
                'components': pca.components_.tolist(),
                'explained variance': pca.explained_variance_.tolist(),
                'explained mean variance': np.mean(pca.explained_variance_.tolist()),
                'explained variance ratio': pca.explained_variance_ratio_.tolist(),
                'mean': pca.mean_.tolist(),
                'n components': pca.n_components_,
                'noise variance': pca.noise_variance_.tolist()
            }
            with open(os.path.join(output_path, 'PCA_results_{}_{}'.format(n, t)),
                      'w') as output:
                json.dump(pca_dict, output)
            pca_components[n, t, :] = \
                pca_dict['components'][0] + pca_dict['components'][1]
    # save the PCA matrix into a .npz file
    np.savez_compressed(os.path.join(output_path, 'components_matrix'), pca_components)
    return pca_components, pca_components.shape


def preform_lead_eig_on_dynamic_connectivity(paths, output_path, brain_areas,
                                            pattern, t_phases, n_subjects, TR):
    """
    Computes the dynamic connectivity of brain areas with leading eigenvectors.

    :param paths: list of paths in input dir
    :type paths: []
    :param output_path: path to output directory
    :type output_path: str
    :param brain_areas: number of brain areas
    :type brain_areas: int
    :param pattern: pattern of input files
    :type pattern: str
    :param t_phases: number of time points
    :type t_phases: int
    :param n_subjects: number of subjects
    :type n_subjects:int
    :param TR: repetition time
    :type TR: int
    :return: leading eigenvectors matrix, leading eigenvectors matrix shape
    :rtype: np.ndarray, tuple
    """
    dFC = np.full((brain_areas, brain_areas), fill_value=0).astype(np.float64)
    l_eigs = np.full((n_subjects, t_phases, brain_areas),
                             fill_value=0).astype(np.float64)
    for n in tqdm(range(n_subjects)):
        phases = convert_to_phases(paths[n], output_path, brain_areas, t_phases, n, TR)
        for t in range(0, t_phases):
            for i in range(0, brain_areas):
                for z in range(0, brain_areas):
                    if np.absolute(phases[i, t] - phases[z, t]) > np.pi:
                        dFC[i, z] = np.cos(2 * np.pi - np.absolute(
                            phases[i, t] - phases[z, t]))
                    else:
                        dFC[i, z] = np.cos(np.absolute(phases[i, t] -
                                                       phases[z, t]))
            dfc_output = os.path.join(output_path, 'dFC')
            create_dir(dfc_output)
            np.savez(os.path.join(dfc_output, 'subject_{}_time_{}'.format(n, t)), dFC)
            eigen_vals, eigen_vects = linalg.eig(dFC)
            leading_eig = eigen_vects[:, eigen_vals.argmax()]
            l_eigs[n, t, :] = leading_eig
    # save the PCA matrix into a .npz file
    np.savez_compressed(os.path.join(output_path, 'components_matrix'), l_eigs)
    return l_eigs, l_eigs.shape


def preform_lle_on_dynamic_connectivity(paths, output_path, brain_areas,
                                        pattern, t_phases, n_subjects, TR):
    """
    Computes the dynamic connectivity of brain areas with performing
    a locally linear embedding returning its matrix.

    :param paths: list of paths in input dir
    :type paths: []
    :param output_path: path to output directory 
    :type output_path: str
    :param brain_areas: number of brain areas
    :type brain_areas: int
    :param pattern: pattern of input files
    :type pattern: str
    :param t_phases: number of time points
    :type t_phases: int
    :param n_subjects: number of subjects
    :type n_subjects:int
    :param TR: repetition time
    :type TR: int
    :return: LLE matrix, LLE matrix shape
    :rtype: np.ndarray, tuple
    """
    dFC = np.full((brain_areas, brain_areas), fill_value=0).astype(np.float64)
    lle_components = np.full((n_subjects, t_phases, (brain_areas * 2)),
                             fill_value=0).astype(np.float64)
    for n in tqdm(range(0, n_subjects)):
        phases = convert_to_phases(paths[n], output_path, brain_areas, t_phases, n, TR)
        for t in range(0, t_phases):
            for i in range(0, brain_areas):
                for z in range(0, brain_areas):
                    if np.absolute(phases[i, t] - phases[z, t]) > np.pi:
                        dFC[i, z] = np.cos(2 * np.pi - np.absolute(
                            phases[i, t] - phases[z, t]))
                    else:
                        dFC[i, z] = np.cos(np.absolute(phases[i, t] -
                                                       phases[z, t]))
            dfc_output = os.path.join(output_path, 'dFC')
            create_dir(dfc_output)
            np.savez(os.path.join(dfc_output, 'subject_{}_time_{}'.format(n, t)),
                dFC)
            lle, err = manifold.locally_linear_embedding(dFC, n_neighbors=12,
                                                         n_components=2)
            with open(os.path.join(output_path, 'LLE_error_{}_{}'.format(n, t)),
                      'w') as output:
                json.dump(err, output)
            lle_components[n, t, :] = np.squeeze(lle.flatten())
    # save the LLE matrix into a .npz file
    np.savez_compressed(os.path.join(output_path, 'components_matrix'), lle_components)
    return lle_components, lle_components.shape


def functional_connectivity_dynamics(reduced_components, output_path):
    """
    Computes the functional connectivity dynamics of brain areas.

    :param reduced_components: reduced components matrix
    :type reduced_components: np.ndarray
    :param output_path: path to output directory 
    :type output_path: str
    :return: FCD matrix
    :rtype: np.ndarray
    """
    n_subjects, t_phases, brain_areas_2 = reduced_components.shape
    FCD = np.full((n_subjects, t_phases, t_phases), fill_value=0)\
        .astype(np.float64)
    # Compute the FCD matrix for each subject as cosine similarity over time
    for subject in tqdm(range(0, n_subjects)):
        for t1 in range(0, t_phases):
            vec_1 = np.squeeze(reduced_components[subject, t1, :])
            for t2 in range(0, t_phases):
                vec_2 = np.squeeze(reduced_components[subject, t2, :])
                # cosine similarity
                FCD[subject, t1, t2] = np.dot(vec_1, vec_2) / (np.linalg.norm(
                    vec_1) * np.linalg.norm(vec_2))
    np.savez_compressed(os.path.join(output_path, 'FCD_matrix'), FCD)
    return FCD
