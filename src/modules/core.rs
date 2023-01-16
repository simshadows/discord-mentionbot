use serenity::prelude::{Context, SerenityError};
use serenity::model::prelude::interaction::application_command::CommandDataOption;
//use serenity::model::id::GuildId;
//use serenity::model::guild::Guild;
use serenity::model::application::command::Command;

pub fn run_help(_options: &[CommandDataOption]) -> String {
    "Not yet implemented!".to_string()
}

pub fn run_ping(_options: &[CommandDataOption]) -> String {
    "Pong!".to_string()
}

// TODO: Implement this?
//#[command]
//async fn servers(ctx: &Context, msg: &Message) -> CommandResult {
//    let http = ctx.http.clone();
//    let guilds = http.get_guilds(None, None).await?;
//    println!("guilds: {:?}", guilds);
//    msg.reply(ctx, format!("{:?}", guilds)).await?;
//
//    Ok(())
//}

// TODO: Do we need this?
//pub async fn register_on_guild_create(ctx: &Context, guild: &Guild) -> Result<(), SerenityError> {
//    let _cmds = GuildId::set_application_commands(&guild.id, &ctx.http, |cmds| {
//        cmds
//            .create_application_command(|cmd| cmd.name("ping").description("Checks for a bot response."))
//            .create_application_command(|cmd| cmd.name("help").description("Displays command help."))
//    }).await?;
//    //println!("I now have the following guild slash commands: {:#?}", _cmds);
//    println!("Registered `core` guild commands for guild: {}", guild.name);
//
//    Ok(())
//}

// TODO: If it really does overwrite commands, we'll need to fix it.
pub async fn register_on_ready(ctx: &Context) -> Result<(), SerenityError> {
    let _cmds = Command::set_global_application_commands(&ctx.http, |cmds| {
        cmds
            .create_application_command(|cmd| cmd.name("ping").description("Checks for a bot response."))
            .create_application_command(|cmd| cmd.name("help").description("Displays command help."))
    }).await?;
    //println!("I now have the following guild slash commands: {:#?}", _cmds);
    println!("Registered `core` global commands.");

    Ok(())
}

