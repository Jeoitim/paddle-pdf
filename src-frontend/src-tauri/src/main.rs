// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::sync::Arc;
use std::sync::Mutex;

use tauri::{Manager, State};

/// Shared state: the HTTP port the Python backend is listening on.
struct BackendState {
    port: Arc<Mutex<Option<u16>>>,
}

fn spawn_backend(mut cmd: std::process::Command, port_state: Arc<Mutex<Option<u16>>>) {
    std::thread::spawn(move || {
        #[cfg(target_os = "windows")]
        {
            // CREATE_NO_WINDOW = 0x08000000
            // Hide the console window of the spawned backend process on Windows in release
            if !cfg!(debug_assertions) {
                use std::os::windows::process::CommandExt;
                cmd.creation_flags(0x08000000);
            }
        }

        let mut child = match cmd
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::inherit())
            .spawn()
        {
            Ok(c) => c,
            Err(e) => {
                eprintln!("[tauri] ERROR: Failed to spawn Python backend: {:?}", e);
                return;
            }
        };

        let stdout = child.stdout.take().expect("No stdout from backend");
        let mut reader = BufReader::new(stdout);
        let mut first_line = String::new();
        if reader.read_line(&mut first_line).is_ok() {
            let port_str = first_line.trim();
            if let Ok(port) = port_str.parse::<u16>() {
                let mut guard = port_state.lock().unwrap();
                *guard = Some(port);
                eprintln!("[tauri] Python backend ready on port {}", port);
            } else {
                eprintln!("[tauri] Failed to parse backend port from: {:?}", port_str);
            }
        }

        // Keep reading stderr for logging (already piped to inherit but drain stdout)
        let _ = child.wait();
    });
}

#[tauri::command]
fn get_backend_port(state: State<'_, BackendState>) -> Option<u16> {
    *state.port.lock().unwrap()
}

fn main() {
    let port_state = Arc::new(Mutex::new(None::<u16>));
    let port_state_clone = port_state.clone();

    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .manage(BackendState { port: port_state })
        .setup(move |app| {
            let port_state_clone = port_state_clone.clone();
            let mut cmd;

            if cfg!(debug_assertions) {
                let manifest_dir = env!("CARGO_MANIFEST_DIR");
                let project_root = std::path::Path::new(manifest_dir)
                    .parent().unwrap()  // src-frontend
                    .parent().unwrap(); // project root
                let dev_backend = project_root
                    .join("backend")
                    .join("dist")
                    .join("paddle_pdf_backend")
                    .join("paddle_pdf_backend.exe");

                if dev_backend.exists() {
                    eprintln!("[tauri] Spawning compiled dev backend: {:?}", dev_backend);
                    cmd = std::process::Command::new(dev_backend);
                } else {
                    // Fall back to running python in the pixi environment
                    let python_exe = project_root
                        .join(".pixi")
                        .join("envs")
                        .join("default")
                        .join("Scripts")
                        .join("python.exe");

                    if python_exe.exists() {
                        eprintln!("[tauri] Backend exe not found. Spawning python backend from pixi environment: {:?}", python_exe);
                        cmd = std::process::Command::new(&python_exe);
                        cmd.args(["-m", "paddle_pdf.app.http_server"]);
                        cmd.env("PYTHONPATH", project_root.join("src"));
                    } else {
                        eprintln!("[tauri] Backend exe not found. Fallback: spawning system python backend");
                        cmd = std::process::Command::new("python");
                        cmd.args(["-m", "paddle_pdf.app.http_server"]);
                        cmd.env("PYTHONPATH", project_root.join("src"));
                    }
                }
            } else {
                // Production: Tauri resolves the sidecar from resources
                let backend_exe = app.path()
                    .resource_dir()
                    .unwrap()
                    .join("paddle_pdf_backend")
                    .join("paddle_pdf_backend.exe");
                eprintln!("[tauri] Spawning production backend sidecar: {:?}", backend_exe);
                cmd = std::process::Command::new(backend_exe);
            }

            spawn_backend(cmd, port_state_clone);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
