// pytauri integration — creates a Python extension module that exports
// `context_factory` and `builder_factory` to the Python side.

use pyo3::prelude::*;

#[pymodule]
#[pyo3(name = "_ext_mod")]
pub fn _ext_mod(m: &Bound<'_, PyModule>) -> PyResult<()> {
    pytauri::pymodule_export(
        m,
        |_args, _kwargs| Ok(tauri::generate_context!()),
        |_args, _kwargs| {
            let builder = tauri::Builder::default()
                .plugin(tauri_plugin_log::Builder::default().build())
                .plugin(tauri_plugin_dialog::init())
                .plugin(tauri_plugin_shell::init());
            Ok(builder)
        },
    )
}
