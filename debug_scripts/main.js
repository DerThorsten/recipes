console.log("hello world");






async function fetchAndPopulate(path, createdDirs) {
    const url = 'prefix/' + path;
    const resp = await fetch(url);
    const data = await resp.arrayBuffer();
    // const uint8Array = new Uint8Array(data);
    // const decoder = new TextDecoder("utf-8");
    // const text = decoder.decode(uint8Array);
    
    const fs_path = "/" + path;

    
    
    // get dir
    const lastSlashIndex = fs_path.lastIndexOf("/");
    if (lastSlashIndex > 0) {
        const dir = fs_path.substring(0, lastSlashIndex);
        if(dir != "/" && !createdDirs.has(dir))
        {   
            console.log("mkdirTree", dir);
            Module.FS.mkdirTree(dir);
            // add dir **and all parent dirs** to createdDirs set
            let currentDir = dir;
            while (currentDir !== "/" && !createdDirs.has(currentDir)) {
                console.log("createdDir", currentDir);
                createdDirs.add(currentDir);
                const parentIndex = currentDir.lastIndexOf("/");
                if (parentIndex > 0) {
                    currentDir = currentDir.substring(0, parentIndex);
                } else {
                    break;
                }
            }
        }
    }
    // console.log("fs_path", fs_path);
    Module.FS.writeFile(fs_path, new Uint8Array(data));
 
}

async function fetchPrefixContent() {
    // store set of created dirs
 var createdDirs = new Set();
  const resp = await fetch("prefix_content.json");
  const data = await resp.json();
  console.log("data", data);
  for (const path of data) {
    await fetchAndPopulate(path, createdDirs);
  }
}


async function main() {
  console.log("hello world from main");
  await fetchPrefixContent();
  const rScriptBody = `
  # R script to test the R WASM build
  print("Hello from R")
  library(reticulate)
  `;
  const rArgs = ["--no-restore", "--vanilla", "-e", rScriptBody];

  // execute the R script
  Module.callMain(rArgs);
}

