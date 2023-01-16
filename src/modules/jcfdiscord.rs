use serenity::prelude::{Context, SerenityError};
use serenity::model::prelude::interaction::application_command::CommandDataOption;
use serenity::model::id::GuildId;
use serenity::model::guild::Guild;
//use serenity::builder::CreateApplicationCommandOption;
//use serenity::model::application::command::CommandOptionType;

//pub fn run_functions(_options: &[CommandDataOption]) -> String {
//    "noot noot".to_string()
//}

pub fn run_swole(_options: &[CommandDataOption]) -> String {
    // TODO: If user is swole, we print "Dude, you so swole <@{}>
    // TODO: If channel is #fitness or channel contains "swole", we print "<#{}> is the best place to get swole with swolebro."
    "Too bad you're not as swole as swolebro".to_string()
}

pub fn run_noot(_options: &[CommandDataOption]) -> String {
    "noot noot".to_string()
}

pub async fn register_on_guild_create(ctx: &Context, guild: &Guild) -> Result<(), SerenityError> {
    let _cmds = GuildId::set_application_commands(&guild.id, &ctx.http, |cmds| {
        cmds
            //.create_application_command(|cmd| cmd.name("functions")
            //    .description("Prints the corresponding MBTI cognitive function stack.")
            //    .add_option(CreateApplicationCommandOption()
            //        .kind(CommandOptionType::SubCommand)
            //        .name("MBTI Type")
            //        .description("The MBTI type")))
            .create_application_command(|cmd| cmd.name("swole")
                .description("are u swole"))
            .create_application_command(|cmd| cmd.name("noot")
                .description("noot noot"))
    }).await?;
    //println!("I now have the following guild slash commands: {:#?}", _cmds);
    println!("Registered `core` guild commands for guild: {}", guild.name);

    Ok(())
}

