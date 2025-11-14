import random
import requests
import time
import json
import os
import sys
import re
import cloudscraper
import sqlite3
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, ContextTypes, filters

TARGET, TYPE, COUNT, USE_PROXY, COUNTRY = range(5)


ADMIN_IDS = [8448769807, 7243305432] 


FORCE_JOIN_CHANNELS = ['@growwithmills', '@dax_channel01', '@daxgrp']  


DB_NAME = 'bot.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users 
                 (user_id INTEGER PRIMARY KEY, is_premium INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()


class TelegramSupportReporter:
    def __init__(self):
        self.report_count = 0
        self.success_count = 0
        self.failed_count = 0
        self.proxies = []
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1"
        ]
        self.country_codes = []
        self.email_domains = []
        self.report_reasons = []
        self.load_resources()
        self.scraper = cloudscraper.create_scraper()
        self.proxy_timeout = 10
        self.valid_proxies = []
        self.support_url = "https://telegram.org/support"

    def load_resources(self):
        # Load country codes with phone number patterns 🌍
        self.country_codes = [
            {"code": "US", "name": "United States", "pattern": "+1###-###-####", "area_codes": ["201", "202", "203", "205", "206", "207", "208", "209", "210", "212"]},
            {"code": "UK", "name": "United Kingdom", "pattern": "+44##-####-####", "area_codes": ["20", "23", "24", "28", "29", "113", "114", "115", "116", "117"]},
            {"code": "DE", "name": "Germany", "pattern": "+49##-###-####", "area_codes": ["30", "40", "69", "89", "211", "221", "231", "241", "251", "261"]},
            {"code": "FR", "name": "France", "pattern": "+33 ###-##-##", "area_codes": ["1", "2", "3", "4", "5", "6", "7", "8", "9"]},
            {"code": "IN", "name": "India", "pattern": "+91##-#####", "area_codes": ["11", "22", "33", "44", "55", "66", "77", "80", "90"]},
            {"code": "RU", "name": "Russia", "pattern": "+7##-###-####", "area_codes": ["495", "499", "812", "813", "814", "815", "816", "817", "818", "820"]},
            {"code": "BR", "name": "Brazil", "pattern": "+55##-#####-####", "area_codes": ["11", "21", "31", "41", "48", "51", "61", "62", "63", "65"]},
            {"code": "CN", "name": "China", "pattern": "+86##-#####-####", "area_codes": ["10", "20", "21", "22", "23", "24", "25", "27", "28", "29"]},
            {"code": "JP", "name": "Japan", "pattern": "+81#-##-####", "area_codes": ["3", "6", "11", "45", "52", "66", "75", "86", "92", "98"]},
            {"code": "NG", "name": "Nigeria", "pattern": "+234##-###-####", "area_codes": ["1", "2", "9", "42", "46", "53", "57", "62", "63", "69"]}
        ]

        # Email domains🙂
        self.email_domains = [
            "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "protonmail.com",
            "aol.com", "icloud.com", "zoho.com", "yandex.com", "mail.com",
            "gmx.com", "hubspot.com", "hey.com", "fastmail.com", "tutanota.com"
        ]

        # Report reasons 🚨
        self.report_reasons = [
            "This account is involved in cryptocurrency scams and fraudulent investment schemes.",
            "This user is impersonating someone and conducting phishing activities.",
            "This account is sending malicious links and conducting hacking activities.",
            "This group is spreading fake news and conducting coordinated inauthentic behavior.",
            "This channel is promoting illegal activities and distributing prohibited content.",
            "This account is involved in romance scams and emotional manipulation for financial gain.",
            "This user is distributing malware and conducting cyber attacks through Telegram.",
            "This account is involved in identity theft and personal information harvesting.",
            "This group is coordinating financial fraud and money laundering activities.",
            "This channel is promoting terrorism and violent extremism content."
        ]

        # Try to load proxies from file if exists 🛡️
        try:
            with open("proxies.txt", "r") as f:
                self.proxies = [line.strip() for line in f if line.strip()]
        except:
            self.proxies = []

        # Try to load custom report messages 📝
        try:
            with open("reports.txt", "r") as f:
                custom_reports = [line.strip() for line in f if line.strip()]
                if custom_reports:
                    self.report_reasons.extend(custom_reports)
        except:
            pass

    def generate_username(self):
        """Generate realistic username 🤖"""
        first_names = ["john", "jane", "mike", "sara", "david", "emma", "chris", "lisa", "alex", "mary"]
        last_names = ["smith", "johnson", "williams", "brown", "jones", "miller", "davis", "garcia", "rodriguez", "wilson"]
        numbers = ["", "123", "456", "789", "2023", "1", "2", "99", "007", "100"]

        pattern = random.choice([
            f"{random.choice(first_names)}{random.choice(last_names)}{random.choice(numbers)}",
            f"{random.choice(first_names)}_{random.choice(last_names)}{random.choice(numbers)}",
            f"{random.choice(first_names)}{random.choice(numbers)}",
            f"{random.choice(last_names)}{random.choice(numbers)}",
            f"{random.choice(first_names)}{random.randint(100, 999)}",
            f"{random.choice(last_names)}{random.randint(1000, 9999)}"
        ])

        return pattern

    def generate_email(self, country_code):
        """Generate a valid and realistic email address 📧"""
        username = self.generate_username()
        domain = random.choice(self.email_domains)
        return f"{username}@{domain}"

    def generate_phone_number(self, country_code):
        """Generate a valid phone number for the given country code 📞"""
        country = next((c for c in self.country_codes if c["code"] == country_code), self.country_codes[0])

        if country_code == "US":
            area_code = random.choice(country["area_codes"])
            exchange = f"{random.randint(200, 999)}"
            line = f"{random.randint(1000, 9999)}"
            return f"+1 {area_code}-{exchange}-{line}"

        elif country_code == "UK":
            area_code = random.choice(country["area_codes"])
            local = f"{random.randint(1000, 9999)}"
            return f"+44 {area_code} {local}"

        elif country_code == "DE":
            area_code = random.choice(country["area_codes"])
            local = f"{random.randint(100000, 999999)}"
            return f"+49 {area_code} {local}"

        # Generic pattern for other countries 🔢
        pattern = country["pattern"]
        phone = ""
        for char in pattern:
            if char == "#":
                phone += str(random.randint(0, 9))
            else:
                phone += char
        return phone

    def get_random_user_agent(self):
        """Get a random user agent 🕵️"""
        return random.choice(self.user_agents)

    def get_random_proxy(self):
        """Get a random proxy if available 🌐"""
        if self.valid_proxies:
            return random.choice(self.valid_proxies)
        elif self.proxies:
            return random.choice(self.proxies)
        return None

    def generate_report_message(self, target, target_type):
        """Generate a realistic report message 📄"""
        base_reason = random.choice(self.report_reasons)

        additions = [
            f"I have evidence of multiple victims who have been affected by {target}.",
            f"This has been ongoing for several weeks now with {target}.",
            f"I'm concerned about the safety of other Telegram users because of {target}.",
            f"Please investigate {target} urgently.",
            f"I can provide additional information about {target} if needed.",
            f"{target} violates Telegram's Terms of Service.",
            f"I've received multiple messages from {target} with malicious intent.",
            f"{target} appears to be part of a larger scam network.",
            f"I'm reporting {target} to protect the community.",
            f"{target} needs to be suspended immediately."
        ]

        return f"{base_reason} {random.choice(additions)}"

    def get_support_page(self):
        """Get the Telegram support page using cloudscraper to bypass Cloudflare 🔓"""
        try:
            # Set random user agent
            self.scraper.headers.update({'User-Agent': self.get_random_user_agent()})

            response = self.scraper.get(self.support_url, timeout=15)

            if response.status_code != 200:
                return None, None

            
            soup = BeautifulSoup(response.text, 'html.parser')

            
            form = soup.find('form')
            if not form:
                return None, None

            form_details = {
                'action': urljoin(self.support_url, form.get('action') or ''),
                'method': form.get('method', 'post').lower(),
                'inputs': []
            }

            # Extract all input fields
            for input_tag in form.find_all('input'):
                input_details = {
                    'name': input_tag.get('name'),
                    'type': input_tag.get('type', 'text'),
                    'value': input_tag.get('value', '')
                }
                form_details['inputs'].append(input_details)

            return form_details, response.cookies

        except Exception as e:
            return None, None

    def submit_support_request(self, target, report_type, email, phone, country, user_agent, proxy=None):
        """Submit a support request to Telegram 📨"""
        try:
            # Get form details
            form_details, cookies = self.get_support_page()
            if not form_details:
                return False, "Failed to get form details ❌"

            # Generate report message
            report_message = self.generate_report_message(target, report_type)

            # Prepare form data
            form_data = {}
            for input_field in form_details['inputs']:
                if input_field['name']:
                    if input_field['name'] == 'email':
                        form_data[input_field['name']] = email
                    elif input_field['name'] == 'phone':
                        form_data[input_field['name']] = phone
                    elif 'message' in input_field['name'].lower():
                        form_data[input_field['name']] = report_message
                    elif 'name' in input_field['name'].lower():
                        # Generates a random name 👤
                        names = ["John Smith", "Jane Doe", "Mike Johnson", "Sarah Williams",
                                 "David Brown", "Emma Davis", "Chris Miller", "Lisa Wilson"]
                        form_data[input_field['name']] = random.choice(names)
                    elif 'subject' in input_field['name'].lower():
                        form_data[input_field['name']] = f"Report {report_type}: {target}"
                    else:
                        form_data[input_field['name']] = input_field['value']

            # Set headers
            headers = {
                'User-Agent': user_agent,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://telegram.org',
                'Referer': self.support_url,
                'Connection': 'close',
                'Upgrade-Insecure-Requests': '1'
            }

            # Prepare proxy
            proxies = None
            if proxy:
                proxies = {
                    'http': f"http://{proxy}",
                    'https': f"http://{proxy}"
                }

            # Submit the form
            response = self.scraper.post(
                url=form_details['action'],
                data=form_data,
                headers=headers,
                cookies=cookies,
                proxies=proxies,
                timeout=20,
                allow_redirects=True
            )

            if response.status_code in [200, 302]:
                self.success_count += 1
                return True, "Success ✅"
            else:
                self.failed_count += 1
                return False, f"HTTP {response.status_code} ❌"

        except Exception as e:
            error_msg = str(e)
            self.failed_count += 1
            return False, error_msg

    async def start_reporting(self, target, report_type="User", count=1, use_proxy=False, country="US", update: Update = None, context: ContextTypes.DEFAULT_TYPE = None):
        """Start the reporting process 🚀"""
        await update.message.reply_text(f"🚀 Starting auto-report for: {target} ({report_type}) 🌟")
        await update.message.reply_text(f"📊 Total reports to send: {count}\n")

        for i in range(count):
            await update.message.reply_text(f"🔄 [{i+1}/{count}] Preparing report... ⚙️")

            # Generate fake user data
            email = self.generate_email(country)
            phone = self.generate_phone_number(country)
            user_agent = self.get_random_user_agent()
            proxy = self.get_random_proxy() if use_proxy else None

            await update.message.reply_text(f"📧 Email: {email}")
            await update.message.reply_text(f"📞 Phone: {phone}")
            if proxy:
                await update.message.reply_text(f"🌐 Proxy: {proxy}")

            # Submit report
            success, msg = self.submit_support_request(
                target=target,
                report_type=report_type,
                email=email,
                phone=phone,
                country=country,
                user_agent=user_agent,
                proxy=proxy
            )

            self.report_count += 1

            if success:
                await update.message.reply_text(f"✅ Report #{i+1} sent successfully! 🎉\n")
            else:
                await update.message.reply_text(f"❌ Report #{i+1} failed: {msg}\n")

            # Random delay to avoid detection💀
            delay = random.uniform(3, 8)
            await update.message.reply_text(f"⏳ Waiting {delay:.1f}s before next report... ⌛")
            time.sleep(delay)

        # Final summary
        await update.message.reply_text(f"\n═══════════════════════════════════\n📈 REPORTING COMPLETE 🌟\n    Total Attempts : {self.report_count} 🔢\n    Successful     : {self.success_count} ✅\n    Failed         : {self.failed_count} ❌\n═══════════════════════════════════")


def add_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def is_premium(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def set_premium(user_id, status=1):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET is_premium = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    total_users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    premium_users = c.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1").fetchone()[0]
    conn.close()
    return total_users, premium_users

# Force join check 🌐
async def has_joined_channels(bot, user_id):
    for channel in FORCE_JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                return False
        except:
            return False  # If error, assume user isn't joined
    return True

# Menu keyboard 🎛️
def get_main_keyboard(is_admin=False):
    keyboard = [
        [KeyboardButton("🚨 Report Target")],
        [KeyboardButton("📊 Bot Stats")]
    ]
    if is_admin:
        keyboard.append([KeyboardButton("➕ Add Premium User")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

# Handlers🙂
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    add_user(user_id)
    is_admin = user_id in ADMIN_IDS
    await update.message.reply_text('👋 Welcome to Telegram Support Reporter Bot! 🌟🌚\nSelect an option below: 👇', reply_markup=get_main_keyboard(is_admin))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    is_admin = user_id in ADMIN_IDS
    reporter = context.bot_data.get('reporter', TelegramSupportReporter())
    context.bot_data['reporter'] = reporter

    if text == "🚨 Report Target":
        # Check premium and force join (bypass for admins/owners) surely na 🙃
        if not is_admin:
            if not is_premium(user_id):
                await update.message.reply_text("⚠️ You need to be a premium user to access reporting! Contact admin to upgrade. 👑")
                return
            if not await has_joined_channels(context.bot, user_id):
                join_text = "🚫 You must join these channels to use the bot:\n"
                for channel in FORCE_JOIN_CHANNELS:
                    join_text += f"- [Join {channel}](https://t.me/{channel[1:]})\n"
                await update.message.reply_text(join_text, parse_mode='Markdown')
                return

        await update.message.reply_text("🎯 Enter the target username/channel/group (e.g., example_user):")
        return TARGET

    elif text == "📊 Bot Stats":
        total, premiums = get_stats()
        stats_text = f"📈 Bot Statistics 🌟\n\n🔢 Total Users: {total}\n👑 Premium Users: {premiums}\n"
        await update.message.reply_text(stats_text)

    elif text == "➕ Add Premium User" and is_admin:
        await update.message.reply_text("➕ Enter the user ID to make premium:")
        return 'ADD_PREMIUM'

    return ConversationHandler.END

# Conversation handlers for report
async def target_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['target'] = update.message.text
    if not context.user_data['target'].startswith('@'):
        context.user_data['target'] = '@' + context.user_data['target']
    await update.message.reply_text("📝 Enter report type (User/Group/Channel) [Default: User]:")
    return TYPE

async def type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['report_type'] = update.message.text or "User"
    await update.message.reply_text("🔢 Enter number of reports [Default: 5]:")
    return COUNT

async def count_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['count'] = int(update.message.text)
    except:
        context.user_data['count'] = 5
    await update.message.reply_text("🌐 Use proxies? (y/n) [Default: n]:")
    return USE_PROXY

async def proxy_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['use_proxy'] = update.message.text.lower() == 'y'
    await update.message.reply_text("🌍 Enter country code (US/UK/DE etc.) [Default: US]:")
    return COUNTRY

async def country_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = update.message.text.upper()
    reporter = context.bot_data['reporter']
    if country not in [c["code"] for c in reporter.country_codes]:
        country = "US"
    context.user_data['country'] = country

    # Start reporting
    await reporter.start_reporting(
        target=context.user_data['target'],
        report_type=context.user_data['report_type'],
        count=context.user_data['count'],
        use_proxy=context.user_data['use_proxy'],
        country=context.user_data['country'],
        update=update,
        context=context
    )
    return ConversationHandler.END

# Add premium handler
async def add_premium_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text)
        set_premium(user_id)
        await update.message.reply_text(f"✅ User {user_id} is now premium! 👑")
    except:
        await update.message.reply_text("❌ Invalid user ID! ⚠️")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Operation cancelled. 👋")
    return ConversationHandler.END

if __name__ == "__main__":
    BOT_TOKEN = "8074948489:AAHn9S8jho1p_I5wYhALNUjev46cPhVvZ3E"

    application = Application.builder().token(BOT_TOKEN).build()
    application.bot_data['reporter'] = TelegramSupportReporter()

    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler)],
        states={
            TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, target_handler)],
            TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, type_handler)],
            COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, count_handler)],
            USE_PROXY: [MessageHandler(filters.TEXT & ~filters.COMMAND, proxy_handler)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country_handler)],
            'ADD_PREMIUM': [MessageHandler(filters.TEXT & ~filters.COMMAND, add_premium_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    application.run_polling()
