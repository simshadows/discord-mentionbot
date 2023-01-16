mod modules;

use std::env;

use serenity::async_trait;
use serenity::prelude::*;
use serenity::model::channel::Message;
use serenity::model::gateway::{Ready, Activity};
use serenity::model::application::interaction::{Interaction, InteractionResponseType};
use serenity::model::guild::Guild;
//use serenity::model::id::GuildId;
//use serenity::model::application::command::Command;

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
        println!("Discovered Username: {}", ready.user.name);
        println!("Discovered Shard ID: {}", ctx.shard_id);

        //// Clear commands
        //Command::set_global_application_commands(&ctx.http, |commands| commands).await.unwrap();

        modules::core::register_on_ready(&ctx).await.unwrap();
        ctx.shard.set_activity(Some(Activity::watching("u sleep")));
    }

    async fn guild_create(&self, ctx: Context, guild: Guild, _: bool) {
        println!("Discovered Guild: {}", guild.name);

        //// Clear commands
        //if let Err(e) = GuildId::set_application_commands(&guild.id, &ctx.http, |commands| commands).await {
        //    println!("Error clearing guild commands: {}", e);
        //}

        //modules::core::register_on_guild_create(&ctx, &guild).await;
        if let Err(e) = modules::jcfdiscord::register_on_guild_create(&ctx, &guild).await {
            println!("Error registering `jcfdiscord` guild commands: {}", e);
        }
    }

    async fn interaction_create(&self, ctx: Context, interaction: Interaction) {
        if let Interaction::ApplicationCommand(command) = interaction {
            println!("Received command interaction: {:#?}", command);

            let content = match command.data.name.as_str() {
                "help" => modules::core::run_help(&command.data.options),
                "ping" => modules::core::run_ping(&command.data.options),
                //"functions" => modules::jcfdiscord::run_functions(&command.data.options),
                "swole" => modules::jcfdiscord::run_swole(&command.data.options),
                "noot" => modules::jcfdiscord::run_noot(&command.data.options),
                _ => {
                    // TODO: Log this as an error
                    "This interaction is not implemented.".to_string()
                },
            };

            if let Err(e) = command
                .create_interaction_response(&ctx.http, |response| {
                    response
                        .kind(InteractionResponseType::ChannelMessageWithSource)
                        .interaction_response_data(|message| message.content(content))
                })
                .await
            {
                println!("Cannot respond to slash command: {}", e);
            }
        }
    }
}

#[tokio::main]
async fn main() {
    let token = env::var("DISCORD_TOKEN").expect("token");
    let intents = GatewayIntents::non_privileged() | GatewayIntents::MESSAGE_CONTENT;
    let mut client = Client::builder(token, intents)
        .event_handler(Handler)
        .await
        .expect("Error creating client");

    // Start a single shard
    if let Err(e) = client.start().await {
        println!("An error occurred while running the client: {:?}", e);
    }
}

