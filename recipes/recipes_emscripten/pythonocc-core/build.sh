#!/bin/bash

mkdir build
cd build

SP_DIR=$PREFIX/lib/python${PY_VER}/site-packages

CXXFLAGS="${CXXFLAGS} -I$SRC_DIR/src/Expr"
export CXXFLAGS

cmake ${CMAKE_ARGS} \
    -D CMAKE_INSTALL_PREFIX:FILEPATH=$PREFIX \
    -D CMAKE_BUILD_TYPE:STRING=Release \
    -D SWIG_HIDE_WARNINGS:BOOL=ON \
    -D PYTHONOCC_INSTALL_DIRECTORY:FILEPATH=$SP_DIR/OCC \
    -D PYTHONOCC_MESHDS_NUMPY:BOOL=ON \
    -D Python3_NumPy_INCLUDE_DIRS=$BUILD_PREFIX/lib/python${PY_VER}/site-packages/numpy/_core/include \
    -D Python3_INCLUDE_DIRS=$PREFIX/include/python3.13/ \
    -D Python3_LIBRARY=$PREFIX/lib/libpython3.13.a \
    -D OCCT_INCLUDE_DIR=$PREFIX/include/opencascade \
    -D OCCT_LIBRARY_DIR=$PREFIX/lib \
    -D OCCT_GP_PNT_HEADER_LOCATION=$PREFIX/include/opencascade/gp_Pnt.hxx \
    -D CMAKE_PROJECT_INCLUDE=$RECIPE_DIR/overwriteProp.cmake \
    ..

emmake make -j${CPU_COUNT} install

# remove lib/python3.13/site-packages/OCC/Core/_Visualization.so

rm -rf $SP_DIR/OCC/Core/_Visualization.so