import os
from flask import Flask, render_template, request, jsonify
import requests
import mysql.connector
import json

app = Flask(__name__)

db = mysql.connector.connect(
    host='localhost',
    user='discord',
    password='password',
    database='databasename'
)

# Function to execute MySQL queries
def execute_query(query, values=None):
    cursor = db.cursor(dictionary=True)
    if values:
        cursor.execute(query, values)
    else:
        cursor.execute(query)
    result = cursor.fetchall()
    db.commit()
    cursor.close()
    return result

# Function to fetch username from ID
def fetch_username(user_id):
    # Logic to fetch username from user_id, replace with your implementation
    return f"User {user_id}"

######################################### API START #################################################

@app.route('/')
def index():
    # Get the username from the request
    username = request.args.get('username', 'Guest')

    # Read user IDs and usernames from database
    admins = execute_query("SELECT * FROM admins")
    owners = execute_query("SELECT * FROM owners")
    users = execute_query("SELECT * FROM users")

    # Pass the admin, owner, and user data to the template
    return render_template('homepage.html', admins=admins, owners=owners, users=users, username=username)


################# SECURITY FUNCTIONALITY #################
@app.route('/discord/adminpanel/verify', methods=['GET', 'POST'])
def verify_admin_panel_access():
    if request.method == 'POST':
        # Check if the X-Discord-ID header is present in the request
        if 'X-Discord-ID' in request.headers:
            user_discord_id = request.headers.get('X-Discord-ID')
            # Perform authentication check against the database
            result = execute_query("SELECT * FROM authenticated_users WHERE user_discord_id = %s", (user_discord_id,))
            if result:
                # Add the user Discord ID to the list of approved IDs
                approved_ids.append(user_discord_id)
                return jsonify({'message': 'Authentication successful', 'user_discord_id': user_discord_id}), 200
            else:
                # Authentication failed due to user not being in the list of authenticated IDs
                print("Authentication failed for user Discord ID:", user_discord_id)
                return jsonify({'message': 'Authentication failed. You are not authorized to access the admin panel.'}), 401
        else:
            # X-Discord-ID header not found in the POST request
            print("X-Discord-ID header not found in POST request")
            return jsonify({'message': 'X-Discord-ID header not found'}), 400
    elif request.method == 'GET':
        # For GET requests, return the list of approved user IDs
        return jsonify({'approved_ids': approved_ids}), 200

@app.route('/adminpanel')
def indext():
    # Get the username from the request
    username = request.args.get('username', 'Guest')

    # Read user IDs and usernames from database
    admins = execute_query("SELECT * FROM admins")
    owners = execute_query("SELECT * FROM owners")
    users = execute_query("SELECT * FROM users")
    guildname = execute_query("SELECT discord_name FROM guild_info")[0]['discord_name']
    
    # Fetch roles from guild_info table
    roles_result = execute_query("SELECT roles FROM guild_info")
    roles = {}
    for row in roles_result:
        if row['roles']:
            roles.update(json.loads(row['roles']))

    # Pass the admin, owner, and user data to the template
    return render_template('dashboard.html', admins=admins, owners=owners, users=users, username=username, roles=roles, guildname=guildname)

################# ADMIN PANEL AND OTHER FUNCTIONALITIES ABOVE #################
@app.route('/update', methods=['POST'])
def update_data():
    # Extract data from the form fields
    admins = request.form.getlist('admins')
    owners = request.form.getlist('owners')
    users = request.form.getlist('users')

    # Update database with the extracted data
    for admin in admins:
        execute_query("INSERT INTO admins (user_id, username) VALUES (%s, %s)", (admin, None))  # Assuming username is nullable
    for owner in owners:
        execute_query("INSERT INTO owners (user_id) VALUES (%s)", (owner,))
    for user in users:
        execute_query("INSERT INTO users (user_id, username) VALUES (%s, %s)", (user, None))  # Assuming username is nullable

    return 'Data updated successfully.'



######################### DISCORD FUNCTIONALITY #########################
@app.route('/userupdate/ban/<user_id>', methods=['POST'])
def ban_user(user_id):
    data = request.json
    reason = data.get('reason', 'Panel Ban')
    action_type = 'ban'  # Define action type
    role_id = data.get('role_id')  # Get role_id from the request

    execute_query("INSERT INTO user_actions (user_id, action_type, reason, role_id) VALUES (%s, %s, %s, %s)",
                  (user_id, action_type, reason, role_id))
    
    return jsonify({'message': f'User with ID {user_id} has been banned. Reason: {reason}'}), 200

@app.route('/userupdate/kick/<user_id>', methods=['POST'])
def kick_user(user_id):
    data = request.json
    reason = data.get('reason', 'Panel Kick')
    action_type = 'kick'  # Define action type
    role_id = data.get('role_id')  # Get role_id from the request

    execute_query("INSERT INTO user_actions (user_id, action_type, reason, role_id) VALUES (%s, %s, %s, %s)",
                  (user_id, action_type, reason, role_id))
    
    return jsonify({'message': f'User with ID {user_id} has been kicked. Reason: {reason}'}), 200

@app.route('/userupdate/addadmin/<user_id>', methods=['POST'])
def add_admin(user_id):
    username = request.json.get('username')
    if user_id and username:
        execute_query("INSERT INTO admins (user_id, username) VALUES (%s, %s)", (user_id, username))
        return jsonify({'message': f'User with ID {user_id} has been added as an admin. Username: {username}'}), 200
    else:
        return jsonify({'error': 'Both user ID and username must be provided'}), 400

@app.route('/userupdate/removeadmin/<user_id>', methods=['POST'])
def remove_admin(user_id):
    execute_query("DELETE FROM admins WHERE user_id = %s", (user_id,))
    return jsonify({'message': f'Admin with ID {user_id} has been removed.'}), 200

@app.route('/userupdate/data', methods=['GET', 'POST'])
def handle_data():
    if request.method == 'GET':
        # Fetch all user actions from the database
        user_actions = execute_query("SELECT * FROM user_actions")
        
        # Fetch user information from the database
        users = execute_query("SELECT * FROM users")

        # Return user actions and user information
        return jsonify({'user_actions': user_actions, 'users': users}), 200
    
    elif request.method == 'POST':
        # Update database with received data
        data = request.form  # Use request.form to access form data sent with POST request
        user_id = data.get('user_id')
        action_type = data.get('action_type')
        reason = data.get('reason', '')  # Reason may not be present for all actions
        role_id = data.get('role_id')  # Get the role_id from the form data
        
        if action_type == 'give_role':
            # Insert into user_actions table for giving role
            execute_query("INSERT INTO user_actions (user_id, action_type, reason, role_id) VALUES (%s, %s, %s, %s)", 
                          (user_id, action_type, reason, role_id))
        elif action_type in ['ban', 'kick', 'add_admin', 'remove_admin']:
            # Insert into user_actions table for other actions (ban, kick, add admin, remove admin)
            execute_query("INSERT INTO user_actions (user_id, action_type, reason, role_id) VALUES (%s, %s, %s, %s)", 
                          (user_id, action_type, reason, None))  # Use None for role_id
        else:
            return jsonify({'error': 'Invalid action type'}), 400

        return jsonify({'message': 'Data updated successfully'}), 200
    
    else:
        return jsonify({'error': 'Unsupported request method'}), 405







# Function to send updated data to the bot
def send_data_to_bot(data):
    # Example of how to process the data in the bot
    print("Received updated data:", data)
    # Further logic to inform the bot about the updated data


############################## GET REQUESTS ##############################
@app.route('/userupdate/banned', methods=['GET'])
def get_banned_users():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter banned users based on user ID
        return jsonify([user for user in banned_users if user['user_id'] == user_id]), 200
    else:
        # Return all banned users if no user ID is provided
        return jsonify(banned_users), 200

@app.route('/userupdate/kicked', methods=['GET'])
def get_kicked_users():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter kicked users based on user ID
        return jsonify([user for user in kicked_users if user['user_id'] == user_id]), 200
    else:
        # Return all kicked users if no user ID is provided
        return jsonify(kicked_users), 200

@app.route('/userupdate/admins', methods=['GET'])
def get_admins():
    user_id = request.args.get('user_id')  # Get the user ID from the query parameters
    if user_id:
        # Filter admins based on user ID
        return jsonify([user for user in admins if user['user_id'] == user_id]), 200
    else:
        # Return all admins if no user ID is provided
        return jsonify(admins), 200

if __name__ == '__main__':
    app.run(debug=True)
