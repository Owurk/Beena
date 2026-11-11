use anyhow::Result;
use serde::{Deserialize, Serialize};
use teloxide::{dispatching::UpdateFilterExt, prelude::*};
use tokio::fs;

const CONFIG_PATH: &str = "telegram.json";

#[derive(Serialize, Deserialize)]
struct TelegramConfig {
    chat_id: i64,
}

async fn get_chat_id() -> Result<Option<i64>> {
    let content = match fs::read_to_string(CONFIG_PATH).await {
        Ok(content) => content,
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
            return Ok(None);
        }
        Err(error) => return Err(error.into()),
    };

    let config: TelegramConfig = serde_json::from_str(&content)?;

    Ok(Some(config.chat_id))
}

async fn save_chat_id(chat_id: i64) -> Result<()> {
    let config = TelegramConfig { chat_id };

    let json = serde_json::to_string_pretty(&config)?;

    fs::write(CONFIG_PATH, json).await?;

    Ok(())
}

async fn handle_message(bot: Bot, msg: Message) -> ResponseResult<()> {
    if msg.text() != Some("/start") {
        return Ok(());
    }

    match get_chat_id().await {
        Ok(Some(existing_id)) => {
            let message = if existing_id == msg.chat.id.0 {
                "Beena notifications are already configured!"
            } else {
                "Beena is already configured with another user."
            };

            bot.send_message(msg.chat.id, message).await?;
            return Ok(());
        }
        Ok(None) => {}
        Err(error) => {
            println!("Failed to read configuration: {error:#}");

            bot.send_message(msg.chat.id, "Failed to read Telegram configuration.")
                .await?;

            return Ok(());
        }
    }

    match save_chat_id(msg.chat.id.0).await {
        Ok(()) => {
            println!("Registered chat_id: {}", msg.chat.id);

            bot.send_message(msg.chat.id, "Beena notifications configured successfully!")
                .await?;
        }
        Err(error) => {
            println!("Failed to save chat_id: {error:#}");

            bot.send_message(msg.chat.id, "Failed to configure notifications.")
                .await?;
        }
    }

    Ok(())
}

#[tokio::main]
async fn main() -> Result<()> {
    dotenvy::dotenv().ok();

    let bot = Bot::from_env();

    let handler = Update::filter_message().endpoint(handle_message);

    println!("Telegram bot started");

    Dispatcher::builder(bot, handler)
        .enable_ctrlc_handler()
        .build()
        .dispatch()
        .await;

    Ok(())
}
