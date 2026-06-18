// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::borrow::Cow;
use std::path::Path;

use pyo3::wrap_pymodule;
use pytauri::standalone::{PythonInterpreterBuilder, PythonInterpreterEnv, PythonScript};

fn main() -> std::process::ExitCode {
    // Determine the Python environment — use the pixi venv
    let venv_root = std::env::var("VIRTUAL_ENV")
        .or_else(|_| {
            let manifest_dir = env!("CARGO_MANIFEST_DIR");
            let pixi_env = Path::new(manifest_dir)
                .parent()        // src-frontend
                .unwrap()
                .parent()        // project root
                .unwrap()
                .join(".pixi/envs/default");
            if pixi_env.exists() {
                Ok(pixi_env.to_string_lossy().to_string())
            } else {
                Err(std::env::VarError::NotPresent)
            }
        })
        .expect("Python environment not found. Set VIRTUAL_ENV or run via `pixi run tauri-dev`");

    // Resolve the project root and src directory for PYTHONPATH
    let manifest_dir = Path::new(env!("CARGO_MANIFEST_DIR"));
    let project_root = manifest_dir.parent().unwrap().parent().unwrap();
    let src_dir = project_root.join("src");

    let current_pythonpath = std::env::var("PYTHONPATH").unwrap_or_default();
    let new_pythonpath = if current_pythonpath.is_empty() {
        src_dir.to_string_lossy().to_string()
    } else {
        format!("{};{}", src_dir.display(), current_pythonpath)
    };
    std::env::set_var("PYTHONPATH", &new_pythonpath);

    let env = PythonInterpreterEnv::Venv(Cow::Owned(Path::new(&venv_root).to_path_buf()));
    let script = PythonScript::Module(Cow::Borrowed("paddle_pdf.app.pytauri_app"));

    let builder = PythonInterpreterBuilder::new(env, script, |py| {
        wrap_pymodule!(app_lib::_ext_mod)(py)
    });

    let interpreter = builder
        .build()
        .expect("Failed to initialize Python interpreter");

    let exit_code = interpreter.run();
    std::process::ExitCode::from(exit_code as u8)
}
