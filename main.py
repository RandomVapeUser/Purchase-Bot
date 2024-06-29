import discord
from discord.ui import Select, View
from discord.ext import commands
from config import data
import asyncio
import json
import os

admins = [749191485001433108, 1160205231334887425]
bot = commands.Bot(command_prefix="?", intents=discord.Intents.all())

@bot.tree.command(description="Redeem a key")
async def redeem(interaction: discord.Interaction, key: str):
    try:
        keys_file = "keys.json"
        database_file = "database.json"

        if not os.path.exists(keys_file):
            await interaction.response.send_message("Key file not found.", ephemeral=True)
            return

        with open(keys_file, "r+") as f:
            keys = json.load(f)
            if key in keys:
                credits = keys.pop(key)
                f.seek(0)
                f.truncate()
                json.dump(keys, f, indent=4)
                await interaction.response.send_message(f"Key redeemed! You received {credits} credits.", ephemeral=True)

                user_id = str(interaction.user.id)
                if os.path.exists(database_file):
                    with open(database_file, "r+") as db_f:
                        database = json.load(db_f)
                        if user_id in database:
                            database[user_id]["balance"] += credits
                        else:
                            database[user_id] = {"balance": credits}

                        db_f.seek(0)
                        json.dump(database, db_f, indent=4)
                else:
                    with open(database_file, "w") as db_f:
                        database = {user_id: {"balance": credits}}
                        json.dump(database, db_f, indent=4)

            else:
                await interaction.response.send_message("Key not found/already redeemed.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)


class RestockModal(discord.ui.Modal, title="Restock an item"):
    def __init__(self, item, interaction):
        super().__init__()
        self.item = item
        self.interaction = interaction

        self.accounts = discord.ui.TextInput(
            label="Accounts (one per line)",
            style=discord.TextStyle.paragraph,
            placeholder="Enter the accounts, one per line",
            required=True
        )

        self.add_item(self.accounts)

    async def on_submit(self, interaction: discord.Interaction):
        accounts = self.accounts.value.strip().split('\n')

        try:
            stock_file = "stock.json"
            if not os.path.exists(stock_file):
                await interaction.response.send_message("Stock file not found.", ephemeral=True)
                return

            with open(stock_file, "r+") as f:
                stock = json.load(f)
                if self.item in stock:
                    stock[self.item]['accounts'].extend(accounts)
                else:
                    stock[self.item] = {
                        "accounts": accounts
                    }

                f.seek(0)
                f.truncate()
                json.dump(stock, f, indent=4)

            await interaction.response.send_message(f"Restocked {self.item}. Added accounts:\n" + "\n".join(accounts), ephemeral=True)

        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

class RestockView(discord.ui.View):
    def __init__(self, items):
        super().__init__()
        self.item_select = discord.ui.Select(
            placeholder="Choose an item to restock...",
            options=[discord.SelectOption(label=item, value=item) for item in items]
        )
        self.item_select.callback = self.select_callback
        self.add_item(self.item_select)

    async def select_callback(self, interaction: discord.Interaction):
        item = self.item_select.values[0]
        await interaction.response.send_modal(RestockModal(item, interaction))

@bot.tree.command(description="Restock an item!")
async def restock(interaction: discord.Interaction):
    if interaction.user.id not in admins:
        await interaction.response.send_message("You cannot run this command.", ephemeral=True)
        return

    stock_file = "stock.json"
    with open(stock_file, "r") as f:
        stock = json.load(f)
        items = list(stock.keys())

    view = RestockView(items)
    await interaction.response.send_message("Select an item to restock:", view=view, ephemeral=True)

@bot.tree.command(description="Show current stock")
async def stock(interaction: discord.Interaction):
    stock_file = "stock.json"
    quantity_1 = 0
    quantity_2 = 0
    quantity_3 = 0
    with open(stock_file, "r") as f:
        stock = json.load(f)

    if stock['Xbox Gamepass Alts (20 Credits)']['accounts'] != []:
        for i in stock['Xbox Gamepass Alts (20 Credits)']['accounts']:
            quantity_1 += 1
    
    if stock['Semi Full Access (50 Credits)']['accounts'] != []:
        for i in stock['Semi Full Access (50 Credits)']['accounts']:
            quantity_2 += 1

    if stock['MCC Unbanned Accounts (10 Credits)']['accounts'] != []:
        for i in stock['MCC Unbanned Accounts (10 Credits)']['accounts']:
            quantity_3 += 1

    embed = discord.Embed(title='Current Stock', color=discord.Color.blue())
    embed.add_field(name='**Xbox Gamepass Alts (20 Credits)**',value=(
            f'**Price:** {stock["Xbox Gamepass Alts (20 Credits)"]["price"]} credits\n'
            f'**Quantity:** {quantity_1}\n'
            ),
            inline=False)
    
    embed.add_field(name='**Semi Full Access (50 Credits)**',value=(
            f'**Price:** {stock["Semi Full Access (50 Credits)"]["price"]} credits\n'
            f'**Quantity:** {quantity_2}\n'
            ),
            inline=False)
    
    embed.add_field(name='**MCC Unbanned Accounts (10 Credits)**',value=(
            f'**Price:** {stock["MCC Unbanned Accounts (10 Credits)"]["price"]} credits\n'
            f'**Quantity:** {quantity_3}\n'
            ),
            inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)

class PurchaseView(View):
    def __init__(self, initial_message, amount):
        super().__init__()
        self.initial_message = initial_message
        self.amount = amount
        self.select = Select(
            placeholder="Select the type of alts...",
            options=[
                discord.SelectOption(label="XGP (20 Credits)", description="Hypixel Unbanned Alts!"),
                discord.SelectOption(label="MCC Unbanned (10 Credits!)", description="MCC Unbanned Alts!"),
                discord.SelectOption(label="Semi Full Access (50 Credits)", description="Permanent Minecraft Accounts but not MFA")
            ]
        )
        self.select.callback = self.on_select
        self.add_item(self.select)

    async def on_select(self, interaction: discord.Interaction):
        selected_label = self.select.values[0]
        user_id_str = str(interaction.user.id)

        with open("stock.json", "r") as file:
            stock_data = json.load(file)

        with open("database.json", "r") as f:
            database = json.load(f)

        account_types = {
            "XGP (20 Credits)": "Xbox Gamepass Alts (20 Credits)",
            "MCC Unbanned (10 Credits!)": "MCC Unbanned Accounts (10 Credits)",
            "Semi Full Access (50 Credits)": "Semi Full Access (50 Credits)"
        }
        account_type = account_types.get(selected_label)
        
        accounts = stock_data.get(account_type, {}).get("accounts", [])

        if stock_data[account_type]["accounts"] == []:
            await interaction.response.send_message(f"No {selected_label} in stock.", ephemeral=True)
            return

        if self.amount > len(accounts):
            await interaction.response.send_message(f"Only {len(accounts)} {selected_label} in stock.", ephemeral=True)
            return

        if user_id_str in database:
            balance = database[user_id_str].get("balance", 0)
            final_money = self.amount * stock_data[account_type]["price"]
            if balance < final_money:
                embed = discord.Embed()
                embed.add_field(name="You do not have enough Credits!")
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        else:
            embed = discord.Embed()
            embed.add_field(name="You do not have enough Credits!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        selected_accounts = accounts[:self.amount]
        accounts_message = "\n".join(selected_accounts)
        user = interaction.user

        try:
            database[user_id_str]["balance"] -= final_money
            with open('database.json', 'w') as f:
                json.dump(database, f, indent=4)
                
            stock_data[account_type]["accounts"] = accounts[self.amount:]
            with open('stock.json', 'w') as file:
                json.dump(stock_data, file, indent=4)
                
            await user.send(f"{accounts_message}") 
        
        except discord.Forbidden:
            embed = discord.Embed()
            embed.add_field(name="I cannot send you a DM. Please check your DM settings.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {str(e)}; Please send this error tho the bot dev (salomao31).", ephemeral=True)

@bot.tree.command(description="Purchase an account")
async def purchase(interaction: discord.Interaction, amount: int):
    if not interaction.channel.type == discord.ChannelType.private:
        await interaction.response.send_message("This command only works in DMs.", ephemeral=True)
        return
    
    initial_message = await interaction.response.send_message("Select the type of alts!", ephemeral=True)
    view = PurchaseView(initial_message, amount)
    await interaction.edit_original_response(view=view)

@bot.tree.command(description="Delete a number of messages in a channel!")
async def purge(interaction: discord.Interaction, number: int):
    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("You do not have permission to purge messages!", ephemeral=True)
        return

    await interaction.response.send_message(f"Purged {number} messages!", ephemeral=True)
    await interaction.channel.purge(limit=number + 1)

@bot.tree.command(description="Check your balance!")
async def balance(interaction: discord.Interaction):
    try:
        database_file = "database.json"

        if not os.path.exists(database_file):
            with open(database_file, "w") as f:
                json.dump({}, f)

        with open(database_file, "r") as f:
            database = json.load(f)
            user_id = str(interaction.user.id)

            if user_id in database:
                balance = database[user_id].get("balance", 0)
                await interaction.response.send_message(f"Your balance is {balance} credits.", ephemeral=True)
            else:
                await interaction.response.send_message("You are not registered in the database. Your balance is 0 credits.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

@bot.tree.command(description="Add coins to a user!")
async def addcoins(interaction: discord.Interaction, user: discord.User, coins: int):
    if interaction.user.id not in admins:
        await interaction.response.send_message("You cannot do that!", ephemeral=True)
        return

    database_file = "database.json"

    if not os.path.exists(database_file):
        with open(database_file, "w") as f:
            json.dump({}, f)

    with open(database_file, "r+") as f:
        database = json.load(f)
        user_id = str(user.id)

        if user_id in database:
            database[user_id]["balance"] += coins
        else:
            database[user_id] = {"balance": coins}
        f.seek(0)
        f.truncate()
        json.dump(database, f, indent=4)

    await interaction.response.send_message(f"Added {coins} coins to {user.name}'s balance.", ephemeral=True)

@bot.tree.command(description="Ban members!")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.ban_members != True:
        await interaction.response.send_message("You do not have the necessary permissions!", ephemeral=True)
        return

    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"Banned **{member.name}**! Reason: {reason}.")
    except Exception as e:
        await interaction.response.send_message(f"{e}, Please send this message to the bot Dev!", ephemeral=True)

@bot.tree.command(description="Kick members!")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = None):
    if interaction.user.guild_permissions.kick_members != True:
        await interaction.response.send_message("You do not have the necessary permissions!", ephemeral=True)
        return

    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"Kicked **{member.name}**! Reason: {reason}.")
    except Exception as e:
        await interaction.response.send_message(f"{e}, Please send this message to the bot Dev!", ephemeral=True)

@bot.tree.command(description="Buy credits for the store!")
async def buycredits(interaction: discord.Interaction):
    embed = discord.Embed(title="Shop Credits")
    embed.add_field(name="You can buy credits at: ",value=">>: https://femb0yalts.mysellix.io/")
    await interaction.response.send_message(embed=embed,ephemeral=True)

@bot.tree.command(description="Debug (Devs Only)")
async def debug(interaction: discord.Interaction):
    if interaction.user.id not in admins:
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return

    try:
        files_to_send = []
        for filename in ["keys.json", "database.json", "stock.json"]:
            if os.path.exists(filename):
                files_to_send.append(discord.File(filename))

        if files_to_send:
            await interaction.response.send_message("Here are the debug files:", files=files_to_send, ephemeral=True)
        else:
            await interaction.response.send_message("No files found to send.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print("Synced!")

bot.run(data['token'])
