use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    tauri_build::build();

    // Only copy Python DLLs next to the exe in RELEASE builds.
    // In debug builds, the Pixi venv already provides the DLLs via the system PATH,
    // and copying them would confuse CPython's prefix resolution (it would think
    // sys.prefix is src-tauri/ instead of the pixi venv root).
    #[cfg(all(target_os = "windows", not(debug_assertions)))]
    {
        let out_dir = env::var("OUT_DIR").unwrap();
        let mut target_dir = PathBuf::from(out_dir);
        target_dir.pop(); // Out directory of build script
        target_dir.pop(); // Crate directory
        target_dir.pop(); // build directory
        // target_dir is now target/<profile>/

        let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
        let project_root = Path::new(&manifest_dir).parent().unwrap().parent().unwrap();

        let pyembed_dir = project_root.join("src-frontend").join("src-tauri").join("pyembed");

        if pyembed_dir.exists() {
            for dll in &["python312.dll", "python3.dll"] {
                let src_dll = pyembed_dir.join(dll);
                let dst_dll = target_dir.join(dll);
                if src_dll.exists() {
                    let _ = fs::copy(&src_dll, &dst_dll);
                }
            }
        }
    }
}
