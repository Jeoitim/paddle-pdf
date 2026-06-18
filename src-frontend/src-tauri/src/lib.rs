#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // Initialize pytauri — loads Python interpreter and registers IPC commands
            // The Python entry point is defined in src/paddle_pdf/app/pytauri_app.py
            app.handle().plugin(
                tauri_plugin_pytauri::Builder::new()
                    .entry_point("paddle_pdf.app.pytauri_app")
                    .build(app.handle())?,
            )?;

            Ok(())
        })
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_shell::init())
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
