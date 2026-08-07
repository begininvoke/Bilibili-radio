#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    env,
    io::{Read, Write},
    net::{TcpListener, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
    thread,
    time::{Duration, Instant},
};

use serde::Serialize;
use tauri::{Emitter, Manager, State, WebviewUrl, WebviewWindow, WebviewWindowBuilder};

const DEFAULT_DESKTOP_PORT: u16 = 41517;
const LYRICS_WINDOW_LABEL: &str = "desktop-lyrics";
const LYRICS_UPDATE_EVENT: &str = "desktop-lyrics:update";

struct BackendState {
    endpoint: Mutex<Option<String>>,
    child: Mutex<Option<Child>>,
}

#[derive(Clone, Serialize)]
struct LyricsPayload {
    enabled: bool,
    text: String,
    color: String,
    title: String,
}

impl BackendState {
    fn new() -> Self {
        Self {
            endpoint: Mutex::new(None),
            child: Mutex::new(None),
        }
    }
}

impl Drop for BackendState {
    fn drop(&mut self) {
        if let Ok(mut child_guard) = self.child.lock() {
            if let Some(mut child) = child_guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

#[tauri::command]
fn desktop_backend_endpoint(state: State<'_, BackendState>) -> Result<String, String> {
    state
        .endpoint
        .lock()
        .map_err(|_| "Backend state lock is poisoned".to_string())?
        .clone()
        .ok_or_else(|| "Desktop backend is not ready".to_string())
}

#[tauri::command]
fn show_lyrics_window(app: tauri::AppHandle) -> Result<(), String> {
    let window = ensure_lyrics_window(&app)?;
    window.show().map_err(|error| error.to_string())?;
    window
        .set_always_on_top(true)
        .map_err(|error| error.to_string())?;
    window
        .set_skip_taskbar(true)
        .map_err(|error| error.to_string())?;
    Ok(())
}

#[tauri::command]
fn hide_lyrics_window(app: tauri::AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window(LYRICS_WINDOW_LABEL) {
        emit_lyrics_payload(
            &app,
            LyricsPayload {
                enabled: false,
                text: "-".to_string(),
                color: "#fb7299".to_string(),
                title: String::new(),
            },
        )?;
        window.hide().map_err(|error| error.to_string())?;
    }
    Ok(())
}

#[tauri::command]
fn set_lyrics_window_payload(
    app: tauri::AppHandle,
    enabled: bool,
    text: String,
    color: String,
    title: String,
) -> Result<(), String> {
    let payload = LyricsPayload {
        enabled,
        text: normalized_lyrics_text(text),
        color: normalized_lyrics_color(color),
        title,
    };

    if enabled {
        let window = ensure_lyrics_window(&app)?;
        window.show().map_err(|error| error.to_string())?;
        window
            .set_always_on_top(true)
            .map_err(|error| error.to_string())?;
    }

    emit_lyrics_payload(&app, payload)
}

fn main() {
    if let Err(error) = run_app() {
        write_startup_error(&format!("{error:#}"));
        panic!("failed to run Bilibili Radio desktop client: {error:#}");
    }
}

fn run_app() -> tauri::Result<()> {
    tauri::Builder::default()
        .manage(BackendState::new())
        .setup(|app| {
            let (endpoint, child) = start_backend(app)?;
            let state = app.state::<BackendState>();
            *state
                .endpoint
                .lock()
                .map_err(|_| "Backend endpoint lock is poisoned".to_string())? = Some(endpoint);
            *state
                .child
                .lock()
                .map_err(|_| "Backend child lock is poisoned".to_string())? = Some(child);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            desktop_backend_endpoint,
            show_lyrics_window,
            hide_lyrics_window,
            set_lyrics_window_payload
        ])
        .run(tauri::generate_context!())
}

fn ensure_lyrics_window(app: &tauri::AppHandle) -> Result<WebviewWindow, String> {
    if let Some(window) = app.get_webview_window(LYRICS_WINDOW_LABEL) {
        return Ok(window);
    }

    WebviewWindowBuilder::new(
        app,
        LYRICS_WINDOW_LABEL,
        WebviewUrl::App("/#/desktop-lyrics".into()),
    )
    .title("Bilibili Radio Lyrics")
    .inner_size(920.0, 112.0)
    .min_inner_size(520.0, 76.0)
    .decorations(false)
    .transparent(true)
    .always_on_top(true)
    .skip_taskbar(true)
    .resizable(true)
    .visible(false)
    .focused(false)
    .build()
    .map_err(|error| error.to_string())
}

fn emit_lyrics_payload(app: &tauri::AppHandle, payload: LyricsPayload) -> Result<(), String> {
    app.emit_to(LYRICS_WINDOW_LABEL, LYRICS_UPDATE_EVENT, payload)
        .map_err(|error| error.to_string())
}

fn normalized_lyrics_text(text: String) -> String {
    let trimmed = text.trim();
    if trimmed.is_empty() {
        "-".to_string()
    } else {
        trimmed.to_string()
    }
}

fn normalized_lyrics_color(color: String) -> String {
    let trimmed = color.trim();
    if trimmed.is_empty() {
        "#fb7299".to_string()
    } else {
        trimmed.to_string()
    }
}

fn write_startup_error(message: &str) {
    let log_path = env::var_os("LOCALAPPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(env::temp_dir)
        .join("Bilibili Radio")
        .join("startup-error.log");
    if let Some(parent) = log_path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(log_path, message);
}

fn start_backend(app: &tauri::App) -> Result<(String, Child), Box<dyn std::error::Error>> {
    let port = choose_backend_port()?;
    let endpoint = format!("http://127.0.0.1:{port}");
    let data_dir = app.path().app_data_dir()?.join("data");
    std::fs::create_dir_all(&data_dir)?;

    let mut command = backend_command(app)?;
    command
        .env("APP_RUNTIME", "desktop")
        .env("AUTH_MODE", "disabled")
        .env("SESSION_COOKIE_SECURE", "false")
        .env("APP_BIND_HOST", "127.0.0.1")
        .env("APP_BIND_PORT", port.to_string())
        .env("APP_DATA_DIR", data_dir)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    let mut child = command.spawn()?;
    if let Err(error) = wait_for_ready(port, Duration::from_secs(25)) {
        let _ = child.kill();
        let _ = child.wait();
        return Err(error.into());
    }

    Ok((endpoint, child))
}

fn backend_command(app: &tauri::App) -> Result<Command, Box<dyn std::error::Error>> {
    if let Ok(exe_path) = env::var("BILIBILI_RADIO_BACKEND_EXE") {
        return Ok(Command::new(exe_path));
    }

    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let dev_entry = manifest_dir
        .parent()
        .and_then(|path| path.parent())
        .map(|path| path.join("py-radio").join("desktop_entry.py"));
    if cfg!(debug_assertions) {
        if let Some(entry) = dev_entry {
            if entry.exists() {
                let python =
                    env::var("BILIBILI_RADIO_PYTHON").unwrap_or_else(|_| "python".to_string());
                let mut command = Command::new(python);
                command.arg(entry);
                return Ok(command);
            }
        }
    }

    let packaged_backend = locate_packaged_backend(app)?;
    Ok(Command::new(packaged_backend))
}

fn locate_packaged_backend(app: &tauri::App) -> Result<PathBuf, Box<dyn std::error::Error>> {
    let resource_dir = app.path().resource_dir()?;
    let direct_backend = resource_dir.join("bilibili-radio-backend.exe");
    if direct_backend.exists() {
        return Ok(direct_backend);
    }

    find_backend_under(&resource_dir).ok_or_else(|| {
        format!(
            "bilibili-radio-backend.exe not found under {}",
            resource_dir.display()
        )
        .into()
    })
}

fn find_backend_under(directory: &std::path::Path) -> Option<PathBuf> {
    let entries = std::fs::read_dir(directory).ok()?;
    for entry in entries.flatten() {
        let path = entry.path();
        if path.is_file()
            && path
                .file_name()
                .and_then(|name| name.to_str())
                .is_some_and(|name| name.eq_ignore_ascii_case("bilibili-radio-backend.exe"))
        {
            return Some(path);
        }
        if path.is_dir() {
            if let Some(found) = find_backend_under(&path) {
                return Some(found);
            }
        }
    }
    None
}

fn reserve_loopback_port() -> std::io::Result<u16> {
    let listener = TcpListener::bind(("127.0.0.1", 0))?;
    let port = listener.local_addr()?.port();
    drop(listener);
    Ok(port)
}

fn choose_backend_port() -> std::io::Result<u16> {
    if let Ok(value) = env::var("BILIBILI_RADIO_DESKTOP_PORT") {
        if let Ok(port) = value.parse::<u16>() {
            return reserve_specific_loopback_port(port).or_else(|_| reserve_loopback_port());
        }
    }

    reserve_specific_loopback_port(DEFAULT_DESKTOP_PORT).or_else(|_| reserve_loopback_port())
}

fn reserve_specific_loopback_port(port: u16) -> std::io::Result<u16> {
    let listener = TcpListener::bind(("127.0.0.1", port))?;
    drop(listener);
    Ok(port)
}

fn wait_for_ready(port: u16, timeout: Duration) -> Result<(), String> {
    let started_at = Instant::now();
    while started_at.elapsed() < timeout {
        if ready_probe(port) {
            return Ok(());
        }
        thread::sleep(Duration::from_millis(250));
    }
    Err(format!("Backend did not become ready on 127.0.0.1:{port}"))
}

fn ready_probe(port: u16) -> bool {
    let address = format!("127.0.0.1:{port}");
    let Ok(mut stream) = TcpStream::connect(address) else {
        return false;
    };
    let _ = stream.set_read_timeout(Some(Duration::from_secs(2)));
    let request = b"GET /health/ready HTTP/1.1\r\nHost: 127.0.0.1\r\nConnection: close\r\n\r\n";
    if stream.write_all(request).is_err() {
        return false;
    }
    let mut response = [0; 64];
    let Ok(bytes_read) = stream.read(&mut response) else {
        return false;
    };
    let head = String::from_utf8_lossy(&response[..bytes_read]);
    head.starts_with("HTTP/1.1 200") || head.starts_with("HTTP/1.0 200")
}
