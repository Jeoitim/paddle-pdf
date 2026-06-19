use std::env;
use std::fs;
use std::path::{Path, PathBuf};

fn main() {
    tauri_build::build();

    // Copy Python DLLs to target directory on Windows for standalone execution during development
    #[cfg(target_os = "windows")]
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
        let pixi_env_dir = project_root.join(".pixi").join("envs").join("default");

        let src_dir = if pyembed_dir.exists() && pyembed_dir.join("python312.dll").exists() {
            pyembed_dir
        } else {
            pixi_env_dir
        };

        if src_dir.exists() {
            for dll in &["python312.dll", "python3.dll"] {
                let src_dll = src_dir.join(dll);
                let dst_dll = target_dir.join(dll);
                if src_dll.exists() {
                    let _ = fs::copy(&src_dll, &dst_dll);
                }
            }
        }
    }
}
