#!/bin/bash
## Start of bash preamble
if [ -z ${CONDA_BUILD+x} ]; then
    source /Users/thorstenbeier/src/recipes/output/bld/rattler-build_occt_1739953506/work/build_env.sh
fi
# enable debug mode for the rest of the script
set -x
## End of preamble

mkdir -p build
cd build


# cxx flags to $PREFIX/include/freetype2/freetype
CXXFLAGS="$CXXFLAGS -I $PREFIX/include/freetype2/freetype -I $PREFIX/include/freetype2/" 
export CXXFLAGS

EMSDK_SYSROOT=$BUILD_PREFIX/opt/emsdk/upstream/emscripten/system

cmake \
      -D BUILD_MODULE_DETools=OFF \
      -D OCCT_NO_PLUGINS=TRUE \
      -D CMAKE_FIND_ROOT_PATH="$PREFIX;$EMSDK_SYSROOT" \
      -D CMAKE_INSTALL_PREFIX:FILEPATH=$PREFIX \
      -D CMAKE_PREFIX_PATH:FILEPATH=$PREFIX \
      -D 3RDPARTY_DIR:FILEPATH=$PREFIX \
      -D BUILD_MODULE_Draw:BOOL=OFF \
      -D USE_TBB:BOOL=OFF \
      -D CMAKE_BUILD_TYPE:STRING="Release" \
      -D BUILD_RELEASE_DISABLE_EXCEPTIONS=OFF \
      -D USE_VTK:BOOL=OFF \
      -D USE_DRACO:BOOL=OFF \
      -D BUILD_MODULE_Draw:BOOL=OFF \
      -D 3RDPARTY_VTK_LIBRARY_DIR:FILEPATH=$PREFIX/lib \
      -D 3RDPARTY_VTK_INCLUDE_DIR:FILEPATH=$PREFIX/include/vtk-9.4 \
      -D USE_FREEIMAGE:BOOL=ON \
      -D USE_FREETYPE:BOOL=OFF \
      -D USE_RAPIDJSON:BOOL=ON \
      -D BUILD_RELEASE_DISABLE_EXCEPTIONS:BOOL=OFF \
      -D QT_HOST_PATH:STRING="${PREFIX}" \
      -D BUILD_SAMPLES_QT=OFF \
      -D BUILD_SHARED_LIBS:BOOL=ON \
      -D BUILD_LIBRARY_TYPE=Shared \
      -D USE_TCL=OFF \
      -D USE_TK=OFF \
      -D CAN_USE_XLIB:BOOL=OFF \
      -D CAN_USE_TK=OFF \
      -D 3RDPARTY_FREETYPE_INCLUDE_DIR_ft2build=$PREFIX/include/freetype2/freetype \
      -D 3RDPARTY_FREETYPE_INCLUDE_DIR_freetype2=$PREFIX/include/freetype2 \
      -D CMAKE_PROJECT_INCLUDE=$RECIPE_DIR/overwriteProp.cmake \
      -D USE_OPENGL:BOOL=OFF \
      -D USE_GLES:BOOL=ON \
      ..


make -j${CPU_COUNT} install