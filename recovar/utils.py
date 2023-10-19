import jax
import numpy as np
import mrcfile, os , psutil

from recovar.fourier_transform_utils import fourier_transform_utils
ftu = fourier_transform_utils(jax.numpy)
    
def find_angle_between_subspaces(v1,v2, max_rank):
    ss = np.conj(v1[:,:max_rank]).T @ v2[:,:max_rank]
    s,v,d = np.linalg.svd(ss)
    if np.any(v > 1.2):
        print('v too big!')
    v = np.where(v < 1, v, 1)
    return np.sqrt( 1 - v[-1]**2)


def subspace_angles(u ,v, max_rank = None):
    max_rank = u.shape[-1] if max_rank is None else max_rank
    corr = np.zeros(max_rank)
    for k in range(1,max_rank+1):
        if k > u.shape[-1]:
            corr[k-1] = 1
        else:
            corr[k-1] = find_angle_between_subspaces(u[:,:k], v[:,:k], max_rank = k )
    return corr  


def estimate_variance(u, s):
    var = np.sum(np.abs(u)**2 * s[...,None], axis = 0)
    return var

# inner psutil function
def get_process_memory_used():
    process = psutil.Process(os.getpid())
    mem_info = process.memory_info()
    return int(mem_info.rss / 1e9)

def get_gpu_memory_total(device =0):
    return int(jax.local_devices()[device].memory_stats()['bytes_limit']/1e9)

def get_gpu_memory_used(device =0):
    return int(jax.local_devices()[device].memory_stats()['bytes_in_use']/1e9)

def get_peak_gpu_memory_used(device =0):
    return int(jax.local_devices()[device].memory_stats()['peak_bytes_in_use']/1e9)

def report_memory_device(device=0, logger=None):
    output_str = f"GPU mem in use:{get_gpu_memory_used(device)}; peak:{get_peak_gpu_memory_used(device)}; total available:{get_gpu_memory_total(device)}, process mem in use:{get_process_memory_used()}"
    if logger is None:
        print(output_str)
    else:
        logger.info(output_str)

def get_size_in_gb(x):
    return x.size * x.itemsize / 1e9
    
def write_mrc(file, ar):
    with mrcfile.new(file, overwrite=True) as mrc:
        mrc.set_data(ar.real.astype(np.float32))

def load_mrc(filepath):
    with mrcfile.open(filepath) as mrc:
        data = mrc.data
    return data
        
def symmetrize_ft_volume(vol, volume_shape):
    og_volume_shape = vol.shape
    vol = vol.reshape(volume_shape)
    vol = vol.at[1:,1:,1:].set( 0.5 * (np.conj(np.flip(vol[1:,1:,1:])) + vol[1:,1:,1:]) )
    return vol.reshape(og_volume_shape)

def get_all_dataset_indices(cryos):
    return np.concatenate([cryo.dataset_indices for cryo in cryos])

def get_inverse_dataset_indices(cryos):
    return np.argsort(np.concatenate([cryo.dataset_indices for cryo in cryos]))

def guess_grid_size_from_vol_size(vol_size):
    return np.round((vol_size)**(1/3)).astype(int)
        
def guess_vol_shape_from_vol_size(vol_size):
    return tuple(3*[guess_grid_size_from_vol_size(vol_size)])

# These should probably be set more intelligently
# Sometimes, memory can grow like O(vol_batch_size * image_batch_size)
def get_image_batch_size(grid_size, gpu_memory):
    return int(2*(2**24)/ (grid_size**2)  * gpu_memory / 38)

def get_vol_batch_size(grid_size, gpu_memory):
    return int(25 * (256 / grid_size)**3 * gpu_memory / 38) 

def get_column_batch_size(grid_size, gpu_memory):
    return int(50 * ((256/grid_size)**3) * gpu_memory / 38)

def get_latent_density_batch_size(test_pts,zdim, gpu_memory):
    return np.max([int(gpu_memory/3 * (get_size_in_gb(test_pts) * zdim**2)), 1])


def make_algorithm_options(args):
    options = {'volume_mask_option': args.mask_option,
    'zs_dim_to_test': args.zdim,
    'contrast' : args.contrast
    }
    return options
