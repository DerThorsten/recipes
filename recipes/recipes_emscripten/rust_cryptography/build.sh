#!/bin/bash


cp $RECIPE_DIR/patches/Cargo.toml  src/rust/Cargo.toml
cp $RECIPE_DIR/patches/setup.py setup.py
# curl https://sh.rustup.rs -sSf | sh -s -- -y
# For RUST
export CARGO_BUILD_TARGET=wasm32-unknown-emscripten
export CARGO_TARGET_WASM32_UNKNOWN_EMSCRIPTEN_LINKER=emcc
export RUST_TOOLCHAIN=nightly-2022-06-26





export PYO3_CROSS_LIB_DIR=${PREFIX}/lib
export PYO3_CROSS_INCLUDE_DIR=${PREFIX}/include

cp ${PREFIX}/etc/conda/_sysconfigdata__emscripten_wasm32-emscripten.py ${PREFIX}/lib

export PYO3_CROSS=1

export PYO3_CONFIG_FILE=$RECIPE_DIR/pyo3_config.ini


# idealy we could automatically include all SIDE_MODULE_LDFLAGS here
export RUSTFLAGS="-C link-arg=-sSIDE_MODULE=2 -C link-arg=-sWASM_BIGINT -Z link-native-libraries=no"


rustup default nightly


export CFLAGS="$CFLAGS -I$BUILD_PREFIX/include  -Wno-implicit-function-declaration"
export LDFLAGS="$LDFLAGS --no-entry -Wl"

export OPENSSL_INCLUDE_PATH=$PREFIX/include
export OPENSSL_LIBRARY_PATH=$PREFIX/lib/libssl.a

source $HOME/.cargo/env && rustup toolchain install $RUST_TOOLCHAIN && rustup default $RUST_TOOLCHAIN
source $HOME/.cargo/env && rustup target add wasm32-unknown-emscripten --toolchain $RUST_TOOLCHAIN

# # rustup toolchain install ${RUST_TOOLCHAIN} && rustup default ${RUST_TOOLCHAIN}
# # rustup target add wasm32-unknown-emscripten --toolchain ${RUST_TOOLCHAIN}
# # TODO: remove this when instant makes a release
git clone --depth 1 https://github.com/hoodmane/instant.git --branch emscripten-no-leading-underscore




${PYTHON} -m pip install .  #|| true

# echo "COPY"

# cp src/rust/target/wasm32-unknown-emscripten/release/cryptography_rust.wasm src/rust/target/wasm32-unknown-emscripten/release/cryptography_rust.so

# ${PYTHON} -m pip install .