# RECOVAR: Regularized covariance estimation for cryo-EM heterogeneity analysis

## Installation
CUDA and [JAX](https://jax.readthedocs.io/en/latest/index.html#) are required to run this code. See information about JAX installation here [JAX](https://jax.readthedocs.io/en/latest/installation.html).

Here is a set of commands which runs on our university cluster (Della), but may need to be tweaked to run on other clusters.

    # module load cudatoolkit/12.2 # You need to load or install CUDA before installing JAX
    conda create --name recovar python=3.9
    conda activate recovar
    pip install --upgrade "jax[cuda12_pip]" -f https://storage.googleapis.com/jax-releases/jax_cuda_releases.html # You may need to pass ax[cuda11_pip] if you use cuda v11
    pip install cryodrgn mrcfile scikit-fmm prody finufft scikit-image tensorflow-cpu matplotlib-scalebar dataframe-image umap-learn[plot] sklearn
    git clone https://github.com/ma-gilles/recovar.git



## I. Preprocessing (copied from [CryoDRGN](https://github.com/ml-struct-bio/cryodrgn#2-parse-image-poses-from-a-consensus-homogeneous-reconstructiqqon))

The input layer of RECOVAR is borrowed directly from the excellent [cryoDRGN toolbox](https://cryodrgn.cs.princeton.edu/). 
Particles, poses and CTF must be prepared in the same way, and below is copy-pasted part of 
[cryoDRGN's documentation](https://github.com/ml-struct-bio/cryodrgn#2-parse-image-poses-from-a-consensus-homogeneous-reconstructiqqon).
CryoDRGN is a dependency, so you should be able to run the commands below after ``conda activate recovar``.

### 1. Preprocess image stack

First resize your particle images using the `cryodrgn downsample` command:

<details><summary><code>$ cryodrgn downsample -h</code></summary>

    usage: cryodrgn downsample [-h] -D D -o MRCS [--is-vol] [--chunk CHUNK]
                               [--datadir DATADIR]
                               mrcs

    Downsample an image stack or volume by clipping fourier frequencies

    positional arguments:
      mrcs               Input images or volume (.mrc, .mrcs, .star, .cs, or .txt)

    optional arguments:
      -h, --help         show this help message and exit
      -D D               New box size in pixels, must be even
      -o MRCS            Output image stack (.mrcs) or volume (.mrc)
      --is-vol           Flag if input .mrc is a volume
      --chunk CHUNK      Chunksize (in # of images) to split particle stack when
                         saving
      --relion31         Flag for relion3.1 star format
      --datadir DATADIR  Optionally provide path to input .mrcs if loading from a
                         .star or .cs file
      --max-threads MAX_THREADS
                         Maximum number of CPU cores for parallelization (default: 16)
      --ind PKL          Filter image stack by these indices

</details>

We recommend first downsampling images to 128x128 since larger images can take much longer to train:

    $ cryodrgn downsample [input particle stack] -D 128 -o particles.128.mrcs

The maximum recommended image size is D=256, so we also recommend downsampling your images to D=256 if your images are larger than 256x256:

    $ cryodrgn downsample [input particle stack] -D 256 -o particles.256.mrcs

The input file format can be a single `.mrcs` file, a `.txt` file containing paths to multiple `.mrcs` files, a RELION `.star` file, or a cryoSPARC `.cs` file. For the latter two options, if the relative paths to the `.mrcs` are broken, the argument `--datadir` can be used to supply the path to where the `.mrcs` files are located.

If there are memory issues with downsampling large particle stacks, add the `--chunk 10000` argument to save images as separate `.mrcs` files of 10k images.


### 2. Parse image poses from a consensus homogeneous reconstruction

CryoDRGN expects image poses to be stored in a binary pickle format (`.pkl`). Use the `parse_pose_star` or `parse_pose_csparc` command to extract the poses from a `.star` file or a `.cs` file, respectively.

Example usage to parse image poses from a RELION 3.1 starfile:

    $ cryodrgn parse_pose_star particles.star -o pose.pkl -D 300

Example usage to parse image poses from a cryoSPARC homogeneous refinement particles.cs file:

    $ cryodrgn parse_pose_csparc cryosparc_P27_J3_005_particles.cs -o pose.pkl -D 300

**Note:** The `-D` argument should be the box size of the consensus refinement (and not the downsampled images from step 1) so that the units for translation shifts are parsed correctly.

### 3. Parse CTF parameters from a .star/.cs file

CryoDRGN expects CTF parameters to be stored in a binary pickle format (`.pkl`). Use the `parse_ctf_star` or `parse_ctf_csparc` command to extract the relevant CTF parameters from a `.star` file or a `.cs` file, respectively.

Example usage for a .star file:

    $ cryodrgn parse_ctf_star particles.star -D 300 --Apix 1.03 -o ctf.pkl

The `-D` and `--Apix` arguments should be set to the box size and Angstrom/pixel of the original `.mrcs` file (before any downsampling).

Example usage for a .cs file:

    $ cryodrgn parse_ctf_csparc cryosparc_P27_J3_005_particles.cs -o ctf.pkl

## II. Specifying a real-space mask

A real space mask is important to boost SNR. Most consensus reconstruction software output a mask, which you can use as input (`--mask-option=input`). Make sure the mask is not too tight, you can use the input `--dilate-mask-iter` to expand the mask if needed. You may also want to use a focusing mask to focus on heterogeneity on one part of the protein, [click here](https://guide.cryosparc.com/processing-data/tutorials-and-case-studies/mask-selection-and-generation-in-ucsf-chimera) to find instructions to generate one with Chimera.

If you don't input a mask, the software will estimate one using the two halfmap means ( `--mask-option=from-halfmaps`). You may also want to run with a loose spherical mask (option `--mask-option=sphere`) and use the computed variance map to observe which parts have large variance.


## III. Running RECOVAR

When the input images (.mrcs), poses (.pkl), and CTF parameters (.pkl) have been prepared, RECOVAR can be run with following command:

    $ python [recovar_directory]/pipeline.py particles.128.mrcs -o output_test --ctf ctf.pkl --poses poses.pkl


<details><summary><code>$ python pipeline.py -h</code></summary>

    usage: pipeline.py [-h] -o OUTDIR [--zdim ZDIM] --poses POSES --ctf pkl [--mask mrc]
    [--mask-option <class 'str'>] [--mask-dilate-iter MASK_DILATE_ITER]
    [--contrast <class 'str'>] [--ind PKL] [--uninvert-data] [--datadir DATADIR]
    [--n-images N_IMAGES] [--padding PADDING] [--halfsets HALFSETS]
    particles

    positional arguments:
    particles             Input particles (.mrcs, .star, .cs, or .txt)

    optional arguments:
    -h, --help            show this help message and exit
    -o OUTDIR, --outdir OUTDIR
                            Output directory to save model
    --zdim ZDIM           Dimension of latent variable
    --poses POSES         Image poses (.pkl)
    --ctf pkl             CTF parameters (.pkl)
    --mask mrc            mask (.mrc)
    --mask-option <class 'str'>
                            mask options: from_halfmaps (default), input, sphere, none
    --mask-dilate-iter MASK_DILATE_ITER
                            mask options how many iters to dilate input mask (only used for input mask)
    --contrast <class 'str'>
                            contrast options: none (option), contrast_qr

    Dataset loading:
    --ind PKL             Filter particles by these indices
    --uninvert-data       Do not invert data sign
    --datadir DATADIR     Path prefix to particle stack if loading relative paths from a .star or .cs
                            file
    --n-images N_IMAGES   Number of images to use (should only use for quick run)
    --padding PADDING     Real-space padding
    --halfsets HALFSETS   Path to a file with indices of split dataset (.pkl).
</details>


The required arguments are:

* an input image stack (`.mrcs` or other listed file types)
* `--poses`, image poses (`.pkl`) that correspond to the input images
* `--ctf`, ctf parameters (`.pkl`), unless phase-flipped images are used
* `-o`, a clean output directory for saving results

Additional parameters which are typically set include:
* `--zdim`, dimensions of PCA to use for embedding, can submit one integer (`--zdim=20`) or a or a command separated list (`--zdim=10,50,100`). Default (`--zdim=4,10,20`).
* `--mask-option` to specify which mask to use
* `--mask` to specify the mask path (`.mrc`)
* `--dilate-mask-iter` to specify a number of dilation of mask
* `--uninvert-data`, Use if particles are dark on light (negative stain format)


## IV. Analyzing results

After the pipeline is run, you can find the mean, eigenvectors, variance maps and embeddings in the `outdir/results` directory, where outdir the option given above by `-o`. You can run some standard analysis by running 

    python analyze.py [outdir] --zdim=10

It will run k-means, generate volumes corresponding to the centers, generate trajectories between pairs of cluster centers and run UMAP. See more input details below.


<details><summary><code>$ python analyze.py -h</code></summary>

    usage: python analyze.py [-h] [-o OUTDIR] [--zdim ZDIM] [--n-clusters <class 'int'>]
                            [--n-trajectories N_TRAJECTORIES] [--skip-umap] [--q <class 'float'>]
                            [--n-std <class 'float'>]
                            result_dir

    positional arguments:
    result_dir            result dir (output dir of pipeline)

    optional arguments:
    -h, --help            show this help message and exit
    -o OUTDIR, --outdir OUTDIR
                            Output directory to save model
    --zdim ZDIM           Dimension of latent variable (a single int, not a list)
    --n-clusters <class 'int'>
                            mask options: from_halfmaps (default), input, sphere, none
    --n-trajectories N_TRAJECTORIES
                            how many trajectories to compute between k-means clusters
    --skip-umap           whether to skip u-map embedding (can be slow for large dataset)
    --q <class 'float'>   quantile used for reweighting (default = 0.95)
    --n-std <class 'float'>
                            number of standard deviations to use for reweighting (don't set q and this
                            parameter, only one of them)

</details>


## V. Generating trajectories



## VI. Using/extending the code

I hope some developpers may find parts of the code useful for their own projects. See [this notebook](recovar_coding_tutorial.ipynb) for a short tutorial.

## Contact

You can reach me (Marc) at mg6942@princeton.edu with questions or comments.