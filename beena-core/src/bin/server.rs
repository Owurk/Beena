use anyhow;
use axum::{
    Router,
    extract::{Json, State},
    http::StatusCode,
    response::IntoResponse,
    routing::post,
};
use reqwest::Client;

use dotenvy;
use serde::{Deserialize, Serialize};
use std::path::{Component, Path, PathBuf};
use teloxide::prelude::*;
use teloxide::types::{ChatId, InputFile};
use tokio::fs;

const CONFIG_PATH: &str = "telegram.json";

#[derive(Deserialize)]
struct TelegramConfig {
    chat_id: i64,
}

#[derive(Serialize, Deserialize, Debug)]
struct SnapshotEvent {
    event_id: String,
    image_path: String,
    detected_class: String,
    confidence: f64,
    local_time: String,
    camera_name: String,
}

#[derive(Debug, Deserialize)]
struct EventAnalysis {
    title: String,
    description: String,
    severity: String,
    is_unusual: bool,
}

#[derive(Debug, Deserialize)]
struct EventAnalysisResponse {
    event_id: String,
    analysis: EventAnalysis,
}

#[derive(Clone)]
struct AppState {
    client: Client,
    bot: Bot,
    shared_storage_root: PathBuf,
}

#[tokio::main]
async fn main() {
    dotenvy::dotenv().ok();

    let client = Client::builder()
        .timeout(std::time::Duration::from_secs(120))
        .build()
        .unwrap();

    let shared_storage_root = PathBuf::from(
        std::env::var("SHARED_STORAGE_ROOT").expect("SHARED_STORAGE_ROOT is not configured"),
    );

    let state = AppState {
        client,
        bot: Bot::from_env(),
        shared_storage_root,
    };

    let app = Router::new()
        .route("/snapshot", post(handle_snapshot))
        .with_state(state);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    println!("Beena core listening on 127.0.0.1:8080");

    axum::serve(listener, app).await.unwrap();
}

async fn handle_snapshot(
    State(state): State<AppState>,
    Json(payload): Json<SnapshotEvent>,
) -> impl IntoResponse {
    println!("event_id: {}", payload.event_id);
    println!("image_path: {}", payload.image_path);
    println!("detected_class: {}", payload.detected_class);
    println!("confidence: {}", payload.confidence);
    println!("camera_name: {}", payload.camera_name);

    println!("Checking Telegram configuration...");

    let chat_id = match get_chat_id().await {
        Ok(Some(chat_id)) => {
            println!("Telegram chat_id loaded: {chat_id}");
            chat_id
        }
        Ok(None) => {
            println!("Telegram configuration not found.");
            return (
                StatusCode::SERVICE_UNAVAILABLE,
                "Telegram bot has not been configured.".to_string(),
            )
                .into_response();
        }
        Err(error) => {
            println!("Failed to read Telegram configuration: {error:#}");
            return (
                StatusCode::INTERNAL_SERVER_ERROR,
                "Failed to read Telegram configuration.".to_string(),
            )
                .into_response();
        }
    };

    println!("Starting AI analysis...");

    let analysis = match analyze_event(&state.client, &payload).await {
        Ok(analysis) => {
            println!("AI analysis completed.");
            analysis
        }
        Err(error) => {
            println!("AI analysis failed: {error:#}");
            return (StatusCode::BAD_GATEWAY, "AI analysis failed.".to_string()).into_response();
        }
    };

    println!("Sending analysis through Telegram...");

    let message = format!(
        "🚨 {}\n\n\
        Description: {}\n\
        Severity: {}\n\
        Unusual: {}\n\
        Event ID: {}",
        analysis.analysis.title,
        analysis.analysis.description,
        analysis.analysis.severity,
        analysis.analysis.is_unusual,
        analysis.event_id,
    );

    let relative_path = Path::new(&payload.image_path);

    if relative_path.is_absolute()
        || relative_path
            .components()
            .any(|component| !matches!(component, Component::Normal(_)))
    {
        println!("Invalid image path: {}", payload.image_path);

        return (StatusCode::BAD_REQUEST, "Invalid image path.".to_string()).into_response();
    }

    let image_path = state.shared_storage_root.join(relative_path);

    if let Err(error) = state
        .bot
        .send_photo(ChatId(chat_id), InputFile::file(&image_path))
        .caption(message)
        .await
    {
        println!("Failed to send Telegram photo: {error:#}");

        return (
            StatusCode::BAD_GATEWAY,
            "Failed to send Telegram notification.".to_string(),
        )
            .into_response();
    }

    println!("Telegram photo sent successfully.");

    StatusCode::ACCEPTED.into_response()
}

async fn analyze_event(
    client: &Client,
    payload: &SnapshotEvent,
) -> anyhow::Result<EventAnalysisResponse> {
    println!("Sending request to AI service...");

    let response = client
        .post("http://127.0.0.1:8001/api/v1/analyze")
        .json(payload)
        .send()
        .await?;

    println!("AI service returned status: {}", response.status());

    let response = response
        .error_for_status()?
        .json::<EventAnalysisResponse>()
        .await?;

    println!("AI analysis completed.");
    println!("Event ID: {}", response.event_id);
    println!("Title: {}", response.analysis.title);
    println!("Description: {}", response.analysis.description);
    println!("Severity: {}", response.analysis.severity);
    println!("Unusual: {}", response.analysis.is_unusual);

    Ok(response)
}

async fn get_chat_id() -> anyhow::Result<Option<i64>> {
    println!("Reading Telegram config from: {}", CONFIG_PATH);

    let content = match fs::read_to_string(CONFIG_PATH).await {
        Ok(content) => content,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            println!("Telegram config file not found.");
            return Ok(None);
        }
        Err(error) => return Err(error.into()),
    };

    println!("Telegram config content: {content}");

    let config: TelegramConfig = serde_json::from_str(&content)?;

    Ok(Some(config.chat_id))
}
