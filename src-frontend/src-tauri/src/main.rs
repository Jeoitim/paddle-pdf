// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::sync::Arc;
use std::sync::Mutex;

use tauri::{AppHandle, Manager, State};

/// Shared state: the HTTP port the Python backend is listening on.
struct BackendState {
    port: Arc<Mutex<Option<u16>>>,
}

fn find_backend_exe(app: &AppHandle) -> PathBuf {
    // In production: sidecar is in resources/paddle_pdf_backend/paddle_pdf_backend.exe
    // In development: use the pixi environment to run http_server.py directly via a wrapper
    if cfg!(debug_assertions) {
        // Development: expect the binary to be next to us, built via
        //   pixi run pyinstaller backend/paddle_pdf_backend.spec
        // OR fall back to running the module directly (set PADDLE_PDF_DEV=1)
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
            return dev_backend;
        }
        // Absolute fallback: caller should handle None
        dev_backend
    } else {
        // Production: Tauri resolves the sidecar from resources
        app.path()
            .resource_dir()
            .unwrap()
            .join("paddle_pdf_backend")
            .join("paddle_pdf_backend.exe")
    }
}

fn spawn_backend(backend_exe: PathBuf, port_state: Arc<Mutex<Option<u16>>>) {
    std::thread::spawn(move || {
        let mut child = std::process::Command::new(&backend_exe)
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::inherit())
            .spawn()
            .expect("Failed to spawn Python backend");

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
            let backend_exe = find_backend_exe(app.handle());
            if !backend_exe.exists() {
                eprintln!(
                    "[tauri] WARNING: Backend executable not found at {:?}\n\
                     Run: pixi run pyinstaller backend/paddle_pdf_backend.spec",
                    backend_exe
                );
            }
            spawn_backend(backend_exe, port_state_clone);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![get_backend_port])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
