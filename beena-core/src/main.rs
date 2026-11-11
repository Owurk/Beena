use axum::{Router, extract::Json, http::StatusCode, routing::post};

use serde::Deserialize;

#[derive(Deserialize, Debug)]
struct SnapshotEvent {
    event: String,
    image_path: String,
    timestamp: String,
}

#[tokio::main]
async fn main() {
    let app = Router::new().route("/snapshot", post(handle_snapshot));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:8080")
        .await
        .unwrap();

    println!("Rust server listening on 127.0.0.1:8080");

    axum::serve(listener, app).await.unwrap();
}

async fn handle_snapshot(Json(payload): Json<SnapshotEvent>) -> StatusCode {
    println!("Received event: {}", payload.event);
    println!("Image path: {}", payload.image_path);
    println!("Timestamp: {}", payload.timestamp);

    // TODO:
    // 1. Load the image.
    // 2. Send it to your AI server.
    // 3. Process the AI response.

    StatusCode::ACCEPTED
}
