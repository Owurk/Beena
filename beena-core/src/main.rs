use anyhow;
use axum::{
    Router,
    extract::{Json, State},
    http::StatusCode,
    routing::post,
};
use reqwest::Client;

use serde::{Deserialize, Serialize};

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

#[tokio::main]
async fn main() {
    let client = Client::new();

    let app = Router::new()
        .route("/snapshot", post(handle_snapshot))
        .with_state(client);

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    println!("Beena core listening on 127.0.0.1:8080");

    axum::serve(listener, app).await.unwrap();
}

async fn handle_snapshot(
    State(client): State<Client>,
    Json(payload): Json<SnapshotEvent>,
) -> StatusCode {
    println!("event_id: {}", payload.event_id);
    println!("image_path: {}", payload.image_path);
    println!("detected_class: {}", payload.detected_class);
    println!("confidence: {}", payload.confidence);
    println!("camera_name: {:?}", payload.camera_name);
    match analyze_event(&client, &payload).await {
        Ok(_) => StatusCode::ACCEPTED,
        Err(error) => {
            eprintln!("AI analysis failed: {error:#}");
            StatusCode::BAD_GATEWAY
        }
    }
}

async fn analyze_event(
    client: &Client,
    payload: &SnapshotEvent,
) -> anyhow::Result<EventAnalysisResponse> {
    let response = client
        .post("http://127.0.0.1:8001/api/v1/analyze")
        .json(payload)
        .send()
        .await?
        .error_for_status()?
        .json::<EventAnalysisResponse>()
        .await?;

    println!("Event ID: {}", response.event_id);
    println!("Title: {}", response.analysis.title);
    println!("Description: {}", response.analysis.description);
    println!("Severity: {}", response.analysis.severity);
    println!("Unusual: {}", response.analysis.is_unusual);

    Ok(response)
}
