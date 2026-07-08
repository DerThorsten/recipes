#!/bin/bash

set -euo pipefail

THIS_DIR=$(dirname "$0")
THIS_DIR=$(cd "${THIS_DIR}" && pwd)
WASM_PREFIX_DIR=${THIS_DIR}/wasm_prefix
echo "WASM_PREFIX_DIR: ${WASM_PREFIX_DIR}"


# if prefix does not exist, create it
if [ ! -d "${WASM_PREFIX_DIR}" ]; then
  echo "Creating WASM_PREFIX_DIR: ${WASM_PREFIX_DIR}"
  $MAMBA_EXE create -y -p "${WASM_PREFIX_DIR}"  \
  -c ${THIS_DIR}/../output \
  -c  https://repo.prefix.dev/emscripten-forge-4x -c conda-forge --platform=emscripten-wasm32 \
  r-base r-py r-reticulate
fi

# create a deployment dir
DEPLOY_DIR=${THIS_DIR}/deploy
rm -rf "${DEPLOY_DIR}/prefix"
rm -rf "${DEPLOY_DIR}/prefix_content.json"
mkdir -p "${DEPLOY_DIR}"

# copy paste relevant r-files to the deployment dir and create dirs if needed
mkdir -p ${DEPLOY_DIR}/prefix/lib
cp -r ${WASM_PREFIX_DIR}/lib/R ${DEPLOY_DIR}/prefix/

# copy shared r libraries to the lib of the prefix dir 
cp ${WASM_PREFIX_DIR}/lib/R/lib/*.so ${DEPLOY_DIR}/prefix/lib

# copy all R shared libs to the deployment dir
cp ${WASM_PREFIX_DIR}/lib/R/lib/*.so ${DEPLOY_DIR}/
# copy all ordenary shared libs to the deployment dir
cp ${WASM_PREFIX_DIR}/lib/*.so ${DEPLOY_DIR}/prefix/lib

# copy the binary to the root of the deployment next to where the html file will be
cp ${WASM_PREFIX_DIR}/lib/R/bin/exec/RPY* ${DEPLOY_DIR}/

# renmae RPY.wasm to R.wasm
mv ${DEPLOY_DIR}/RPY.wasm ${DEPLOY_DIR}/R.wasm


# copy the index.html file to the deployment dir
cp ${THIS_DIR}/index.html ${DEPLOY_DIR}/
# copy main.js to the deployment dir
cp ${THIS_DIR}/main.js ${DEPLOY_DIR}/


python $THIS_DIR/tree.py ${DEPLOY_DIR}/prefix  ${DEPLOY_DIR}/prefix_content.json


python -m http.server 8000 --directory ${DEPLOY_DIR}