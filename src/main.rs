use std::env;

use serenity::async_trait;
use serenity::prelude::*;
use serenity::model::channel::Message;
use serenity::model::gateway::{Ready, Activity};
use serenity::framework::standard::macros::{command, group, hook};
use serenity::framework::standard::{StandardFramework, CommandResult};

#[group]
#[commands(
    help,
    ping,
    servers,
)]
struct General;

struct Handler;

#[async_trait]
impl EventHandler for Handler {
    async fn message(&self, ctx: Context, msg: Message) {
        let channel_name = match msg.channel_id.name(ctx.cache).await {
            Some(s) => s,
            None => "(no channel name)".to_string(),
        };
        println!("#{} [{}#{}]: {}", channel_name, msg.author.name, msg.author.discriminator, msg.content);
    }

    async fn ready(&self, ctx: Context, ready: Ready) {
        let http = ctx.http.clone();

        println!("Username: {}", ready.user.name);
        println!("Shard ID: {}", ctx.shard_id);

        match http.get_guilds(None, None).await {
            Ok(guilds) => {
                for guild in guilds.iter() {
                    println!("Found guild: {}", guild.name);
                }
            },
            Err(e) => {
                println!("'get_guilds' Error: {:?}", e);
            }
        };

        ctx.shard.set_activity(Some(Activity::watching("u sleep")));
    }
}

#[tokio::main]
async fn main() {
    let framework = StandardFramework::new()
        .configure(|c| c.prefix("!"))
        .unrecognised_command(unrecognized_command_hook)
        .group(&GENERAL_GROUP);

    let token = env::var("DISCORD_TOKEN").expect("token");
    let intents = GatewayIntents::non_privileged() | GatewayIntents::MESSAGE_CONTENT;
    let mut client = Client::builder(token, intents)
        .event_handler(Handler)
        .framework(framework)
        .await
        .expect("Error creating client");

    // Start a single shard
    if let Err(why) = client.start().await {
        println!("An error occurred while running the client: {:?}", why);
    }
}

#[hook]
async fn unrecognized_command_hook(_: &Context, _: &Message, cmd_name: &str) {
    println!("Unrecognized command: {}", cmd_name);
}

#[command]
async fn help(ctx: &Context, msg: &Message) -> CommandResult {
    msg.reply(ctx, "Not yet implemented.").await?;

    Ok(())
}

#[command]
async fn servers(ctx: &Context, msg: &Message) -> CommandResult {
    let http = ctx.http.clone();
    let guilds = http.get_guilds(None, None).await?;
    println!("guilds: {:?}", guilds);
    msg.reply(ctx, format!("{:?}", guilds)).await?;

    Ok(())
}

#[command]
async fn ping(ctx: &Context, msg: &Message) -> CommandResult {
    msg.reply(ctx, "Pong!").await?;

    Ok(())
}

