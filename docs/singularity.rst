===========
Singularity
===========

:code:`bilby_pipe` is a lightweight code for setting up parameter estmation for
gravitational wave signals on the LIGO Data Grid clusters. The actual heavy
lifting of running parameter is done by `bilby
<https://git.ligo.org/lscsoft/bilby>`_. We provide a `singularity container
<https://www.sylabs.io/guides/2.6/user-guide/index.html>`_ for bilby_pipe which
has all the prerequisite software (e.g.., :code:`bilby`, `lalsuite
<https://git.ligo.org/lscsoft/lalsuite>`_, `gwpy <https://gwpy.github.io/>`_,
and `all supported bilby samplers
<https://lscsoft.docs.ligo.org/bilby/samplers.html>`_.

A container can be thought of as a lightweight virtual machine which hosts the
software. Using containers decreases the start-up difficulty and also aids in
ensuring that results are reproducible since we can know the versions of all
software used in the container.

:code:`singularity` is installed on all LIGO Data Grid (LDG) clusters. To
install it on your local machine, see `the installation instructions
<https://www.sylabs.io/guides/2.6/user-guide/installation.html>`_.

Obtaining a singularity image
-----------------------------

All the singularity containers are hosted on `singularity-hub
<https://www.singularity-hub.org/collections/2050>`_. Whilst working on one of
the LDG clusters, you can "pull" a container:

.. code-block:: console

   $ singularity pull shub://lscsoft/bilby_pipe:dev

Here, :code:`shub://` indicates to singularity that you want to pull from
singularity-hub, then the remaining path is the URI. The part of the URI
following the colon is the "tag". We intend to maintain two types of tags:

1. Release tags, e.g. :code:`:0.0.1`, for each release of :code:`bilby_pipe` a
   singularity image will be provided. The :code:`bilby` version will be set by
   the latest `bilby-PyPI version <https://pypi.org/project/bilby/>`_ at the
   time of the release.

2. A development tag :code:`:tag` which will be manually built from the master
   branch of bilby_pipe and bilby. Unfortunately, it is not possible yet to
   have this update automatically with all changes to master, although we will
   work on adding this in future.

Using a singularity image
-------------------------

After pulling the image, one should see something like this

.. code-block:: console

   $ singularity pull shub://lscsoft/bilby_pipe:dev
   Progress |===================================| 100.0%
   Done. Container is at: /home/gregory.ashton/lscsoft-bilby_pipe-master-dev.simg

The final line provides a path to where the container was downloaded too. The
container is an executable version of :code:`bilby_pipe`. To see what it can
do, run

.. code-block:: console

   $ ./lscsoft-bilby_pipe-master-dev.simg --help
   14:31 bilby_pipe INFO    : Running bilby_pipe version: 0.0.1: (CLEAN) 81118ee 2019-01-04 16:39:08 +1100
   usage:
   bilby_pipe is a command line tools for taking user input (as command line
   arguments or an ini file) and creating DAG files for submitting bilby parameter
   estimation jobs.

   ...

(note the use of :code:`./` before the container path, this "executes" the
container).

The container is equivalent to calling :code:`bilby_pipe`. I.e., all of the
commands given in `Using bilby_pipe <user-interface.txt>`_ can equivalently be
run instead by executing the container image and providing the neccersery
command line arguments.

.. note::

   You may wish to define an alias in your :code:`.bashrc` such as

   .. code-block:: console

      alias bilby_pipe='./PATH/TO/CONTAINER.simg

   Use an absolute path to ensure :code:`bilby_pipe` can be called from anywhere.


Building a custom container
---------------------------

Singularity images can be built in a number of ways. For full instructions,
please refer to the `official documentation
<https://www.sylabs.io/guides/2.6/user-guide/quick_start.html#build-images-from-scratch>`_.

The cleanest way to generate an image is using a `container recipe
<https://www.sylabs.io/guides/2.6/user-guide/container_recipes.html>`_. For an
example, see the `bilby_pipe build recipes
<https://git.ligo.org/lscsoft/bilby_pipe/blob/master/containers/>`_ (files
starting with :code:`Singularity`.

Unfortunately, :code:`singularity` requires root access to build from a recipe.
As such, it is not possible to build recipes on the LIGO Data Grid clusters.
Instead, one can install a local copy of :code:`singularity`. Alternatively one
can use singularity-hub to set up automatic
building of containers from a connected github account.
