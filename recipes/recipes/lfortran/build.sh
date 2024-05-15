#!/usr/bin/env bash

set -e
set -x

mkdir -p ${PREFIX}/etc/conda/activate.d
mkdir -p ${PREFIX}/etc/conda/deactivate.d

cp "${RECIPE_DIR}"/activate-lfortran.sh   ${PREFIX}/etc/conda/activate.d/activate_z-${PKG_NAME}.sh
cp "${RECIPE_DIR}"/deactivate-lfortran.sh ${PREFIX}/etc/conda/deactivate.d/deactivate_z-${PKG_NAME}.sh


CONDA_EMSDK_DIR_CONFIG_FILE=$HOME/.emsdkdir
if test -f "$CONDA_EMSDK_DIR_CONFIG_FILE"; then
    echo "Found config file $CONDA_EMSDK_DIR_CONFIG_FILE"
else
    # return an error
    echo "Config file $CONDA_EMSDK_DIR_CONFIG_FILE not found"
    return 1
fi

export EMSDK_DIR=$(<$CONDA_EMSDK_DIR_CONFIG_FILE)

# run build0.sh
sh ./build0.sh




# run **what build1.sh does**

cmake \
    -DCMAKE_BUILD_TYPE=Debug \
    -DWITH_LLVM=yes \
    -DLFORTRAN_BUILD_ALL=yes \
    -DWITH_STACKTRACE=yes \
    -DWITH_RUNTIME_STACKTRACE=yes \
    -DCMAKE_PREFIX_PATH="$CMAKE_PREFIX_PATH_LFORTRAN;$PREFIX;$BUILD_PREFIX" \
    -DCMAKE_INSTALL_PREFIX=$PREFIX \
    -DCMAKE_INSTALL_LIBDIR=share/lfortran/lib \
    .
cmake --build . -j2 --target install