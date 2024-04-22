import discord
from discord.ext import commands
import mysql.connector
from dotenv import load_dotenv
import os
import asyncio
import requests
import json

# Load environment variables
load_dotenv()

# Get the token from environment variables
TOKEN = os.getenv('DISCORD_TOKEN')

# API endpoint URL
API_URL = "http://localhost:5000/update"
UPDATES_URL = "http://localhost:5000/userupdate"
APIVERIFY_URL = 'http://localhost:5000'

# Connect to the MySQL database
db = mysql.connector.connect(
    host='localhost',
    user='username',
    password='password',
    database='databasename'
)

# Create bot instance with intents
intents = discord.Intents.all()
bot = commands.Bot(command_prefix='-', intents=intents)

# Function to check if the author of the message is an admin
async def is_admin(ctx):
    cursor = db.cursor()
    sql = "SELECT * FROM admins WHERE discord_id = %s"
    cursor.execute(sql, (ctx.author.id,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

# Function to check if the author of the message is an owner
async def is_owner(ctx):
    cursor = db.cursor()
    sql = "SELECT * FROM owners WHERE discord_id = %s"
    cursor.execute(sql, (ctx.author.id,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None


# Function to get user IDs from the guild
def get_user_ids(guild):
    return [member.id for member in guild.members]

# Function to get user IDs and usernames from the guild
def get_user_data(guild):
    return [(member.id, member.name) for member in guild.members]

async def send_update_request(guild_id):
    last_sent_admins = set()
    last_sent_owners = set()

    while True:
        try:
            # Fetch current admin and owner IDs from the database
            current_admins = set(get_admin_ids())
            current_owners = set(get_owner_ids())

            # Check if admin or owner IDs have changed
            if current_admins != last_sent_admins or current_owners != last_sent_owners:
                data = {
                    "admins": list(current_admins),
                    "owners": list(current_owners),
                    "users": get_user_data_from_guild(guild_id)
                }

                # Send data to the API endpoint
                # Modify this part according to how you send data to your API
                # Example: execute_query("INSERT INTO api_data (admins, owners, users) VALUES (%s, %s, %s)",
                #                        (json.dumps(list(current_admins)), json.dumps(list(current_owners)), json.dumps(get_user_data_from_guild(guild_id))))
                #print("Data sent to API successfully!")
                # Update last sent IDs
                last_sent_admins = current_admins
                last_sent_owners = current_owners
            else:
                #print("No changes detected in admin or owner IDs.")
                pass

            await asyncio.sleep(60)  # Adjust the interval as needed
        except Exception as e:
            print(f"An error occurred: {e}")


# Function to fetch admin IDs from MySQL
def get_admin_ids():
    cursor = db.cursor()
    cursor.execute("SELECT discord_id FROM admins")
    return [row[0] for row in cursor.fetchall()]

# Function to fetch owner IDs from MySQL
def get_owner_ids():
    cursor = db.cursor()
    cursor.execute("SELECT discord_id FROM owners")
    return [row[0] for row in cursor.fetchall()]


def get_user_data_from_guild(guild_id):
    # Implement your logic to fetch user data from the guild
    # This could involve querying the guild object directly or through the Discord API
    # Return the user data in the desired format (e.g., list of tuples)
    pass


# Command to clear messages
@bot.command(name="clear", aliases=["cl"], brief="Clear a certain amount of messages")
@commands.check(lambda ctx: is_owner(ctx) or is_admin(ctx))
async def clear(ctx, amount: int = 25):
    await ctx.channel.purge(limit=amount)

# Command to list all users in the guild
@bot.command(name='list_users')
async def list_users(ctx):
    guild = ctx.guild
    cursor = db.cursor()
    cursor.execute("SELECT username FROM users WHERE guild_id = %s", (guild.id,))
    users = [row[0] for row in cursor.fetchall()]
    cursor.close()
    user_list = ', '.join(users)
    await ctx.send(f'All users: {user_list}')

# Command to add an admin
@bot.command(name='addadmin')
@commands.check(is_owner)
async def add_admin(ctx, member: discord.Member):
    try:
        cursor = db.cursor()
        sql = "INSERT INTO admins (discord_id, username) VALUES (%s, %s)"
        cursor.execute(sql, (member.id, member.name))
        db.commit()
        cursor.close()
        await ctx.send(f'{member.name} has been added as an admin.')
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')

# Command to kick a user
@bot.command(name='kick', pass_context=True)
@commands.has_permissions(kick_members=True)
@commands.check(is_admin)
async def kick_user(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f'Kicked {member.name} from the server. Reason: {reason}')

# Command to get the ID of a user
@bot.command(name='get_user_id')
@commands.check(is_admin)
async def get_user_id(ctx, member: discord.Member):
    await ctx.send(f"The user's ID is: {member.id}")

# Command to add the invoker as an admin
@bot.command(name='AdminMe')
async def admin_me(ctx):
    try:
        cursor = db.cursor()
        # Check if the author is already an admin
        cursor.execute("SELECT * FROM admins WHERE discord_id = %s", (ctx.author.id,))
        result = cursor.fetchone()
        if result:
            await ctx.send("You're already an admin.")
            cursor.close()
            return

        # Check if the author is the owner
        cursor.execute("SELECT * FROM owners WHERE discord_id = %s", (ctx.author.id,))
        result = cursor.fetchone()
        if result:
            await ctx.send("Sorry, you're already the owner.")
            cursor.close()
            return

        # Add the author as an admin
        sql = "INSERT INTO admins (discord_id, username) VALUES (%s, %s)"
        cursor.execute(sql, (ctx.author.id, ctx.author.name))
        db.commit()
        cursor.close()
        
        await ctx.send("You've been added as an admin.")
    except Exception as e:
        await ctx.send(f'An error occurred: {e}')


# Command to manually send update request
@bot.command(name="update")
async def update(ctx):
    try:
        # Check if the author is the owner or an admin
        if await is_owner(ctx) or await is_admin(ctx):
            for guild in bot.guilds:
                await send_update_request(guild.id)  # Send update request for each guild
            await ctx.send("Update request sent to all guilds.")
        else:
            await ctx.send("You don't have permission to use this command.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")


# Function to get username from ID
def get_username(user_id, users_data):
    for uid, username in users_data:
        if uid == user_id:
            return username
    return "Unknown"


async def authenticate_command(ctx):
    try:
        # Get the Discord user ID
        user_discord_id = str(ctx.author.id)

        # Check if the user's ID is present in the authenticated_users table
        if is_user_authenticated(user_discord_id):
            await ctx.author.send("Authentication successful. Here is the link to access the admin panel: http://localhost:5000/discord/adminpanel")
            await ctx.send("Check your private messages for the authentication link.")
        else:
            await ctx.author.send("You are not authorized to access the admin panel.")

    except Exception as e:
        await ctx.author.send(f"An error occurred while authenticating: {e}")


def is_user_authenticated(user_discord_id):
    cursor = db.cursor()
    cursor.execute("SELECT * FROM authenticated_users WHERE discord_id = %s", (user_discord_id,))
    result = cursor.fetchone()
    cursor.close()
    return result is not None

################### API HANDLING BELOW ###################
async def give_role(guild, user_id, role_id):
    try:
        # Fetch the user and the role objects
        user = await guild.fetch_member(user_id)
        role = discord.utils.get(guild.roles, id=role_id)
        
        # Check if the user and role objects exist
        if user is None:
            print(f"User with ID {user_id} not found.")
            return
        if role is None:
            print(f"Role with ID {role_id} not found.")
            return
        
        # Give the role to the user
        await user.add_roles(role)
        print(f"Role {role.name} added to user {user.display_name}.")
        
    except Exception as e:
        print(f"An error occurred while giving role: {e}")


async def handle_api_requests(guild):
    while True:
        try:
            cursor = db.cursor(dictionary=True)

            # Get data from the /userupdate/data endpoint
            data_url = f"{UPDATES_URL}/data"
            response = requests.get(data_url)
            if response.status_code == 200:
                # Parse response content as JSON
                data = response.json()

                # Process user actions
                for action_data in data.get('user_actions', []):
                    user_id = action_data['user_id']
                    action_type = action_data['action_type']
                    reason = action_data.get('reason', f'Panel {action_type.capitalize()}')

                    # Handle specific actions
                    if action_type == 'ban':
                        # Ban the user
                        await ban_user(guild, user_id, reason)
                    elif action_type == 'kick':
                        # Kick the user
                        await kick_user(guild, user_id, reason)
                    elif action_type == 'give_role':
                        # Give a role to the user
                        role_id = action_data['role_id']
                        await give_role(guild, user_id, role_id)
                    # Remove the entry from the database
                    cursor.execute("DELETE FROM user_actions WHERE user_id = %s AND action_type = %s",
                                   (user_id, action_type))
                    db.commit()

            cursor.close()
        except Exception as e:
            print(f"An error occurred while handling API requests: {e}")
        await asyncio.sleep(20)  # Adjust the interval as needed





async def send_guild_info_to_db(bot):
    while True:
        try:
            # Get the guild
            guild = bot.guilds[0]

            # Fetch the owner's member object
            owner = await guild.fetch_member(guild.owner_id)

            # Get all roles in the guild except @everyone
            roles_info = {}
            for role in guild.roles:
                if role.name != '@everyone':
                    roles_info[str(role.id)] = role.name

            # Convert roles_info to a JSON string
            roles_json = json.dumps(roles_info)

            # Check if guild information already exists in the database
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM guild_info WHERE guild_id = %s", (str(guild.id),))
            existing_data = cursor.fetchone()
            cursor.close()

            if existing_data:
                # Check if roles are different
                existing_roles_json = existing_data['roles']
                if roles_json != existing_roles_json:
                    # Update roles in the database
                    cursor = db.cursor()
                    cursor.execute(
                        "UPDATE guild_info SET roles = %s WHERE guild_id = %s",
                        (roles_json, str(guild.id))
                    )
                    db.commit()
                    cursor.close()
                    print("Guild roles updated in the database.")

            else:
                # Insert new guild information into the database
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO guild_info (guild_id, guild_owner, discord_name, roles) VALUES (%s, %s, %s, %s)",
                    (str(guild.id), str(owner.id), guild.name, roles_json)
                )
                db.commit()
                cursor.close()
                print("New guild information inserted into the database.")

            # Insert users into the database
            for member in guild.members:
                # Check if user already exists in the database
                cursor = db.cursor(dictionary=True)
                cursor.execute("SELECT * FROM users WHERE discord_id = %s", (str(member.id),))
                existing_user = cursor.fetchone()
                cursor.close()

                if not existing_user:
                    # Insert user into the database
                    cursor = db.cursor()
                    cursor.execute(
                        "INSERT INTO users (discord_id, username) VALUES (%s, %s)",
                        (str(member.id), member.name)
                    )
                    db.commit()
                    cursor.close()
            #print("Users information inserted into the database.")

            # Insert guild owner into the database
            # Check if guild owner already exists in the database
            cursor = db.cursor(dictionary=True)
            cursor.execute("SELECT * FROM owners WHERE discord_id = %s", (str(owner.id),))
            existing_owner = cursor.fetchone()
            cursor.close()

            if not existing_owner:
                # Insert guild owner into the database
                cursor = db.cursor()
                cursor.execute(
                    "INSERT INTO owners (discord_id, username) VALUES (%s, %s)",
                    (str(owner.id), owner.name)
                )
                db.commit()
                cursor.close()
                print("Guild owner information inserted into the database.")

        except Exception as e:
            print(f"An error occurred while processing guild information: {e}")


        # Wait for 10 seconds before the next refresh
        await asyncio.sleep(10)






async def update_on_ready():
    await bot.wait_until_ready()
    for guild in bot.guilds:
        # No need for update_files() anymore
        bot.loop.create_task(send_update_request(guild.id))
        bot.loop.create_task(handle_api_requests(guild))

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    bot.loop.create_task(update_on_ready())
    await send_guild_info_to_db(bot)

# Remove the functions that load admin IDs and owner IDs from files

# Run the bot
bot.run(TOKEN)
