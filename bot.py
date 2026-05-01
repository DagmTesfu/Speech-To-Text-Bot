import os
import re
import tempfile
import whisper
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Load token from .env file
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ No TELEGRAM_BOT_TOKEN found in .env file!")

# Regular expression to find 12 words
TWELVE_WORD_PATTERN = r'\b(?:\w+(?:[-]\w+)?\s+){11}\w+(?:[-]\w+)?\b'

# Global variables for the race game
race_active = False
winner = None
first_transcript = None

# Load Whisper model
print("🔄 Loading Whisper model...")
model = whisper.load_model("base")
print("✅ Whisper model ready!")

# ===== HELPER FUNCTIONS =====

async def transcribe_audio(file_path: str) -> str:
    """Transcribe audio file using Whisper"""
    try:
        result = model.transcribe(file_path)
        return result["text"]
    except Exception as e:
        print(f"Transcription error: {e}")
        return f"Error transcribing: {str(e)}"

def find_twelve_words(text: str) -> str or None:
    """Extract 12 consecutive words from text"""
    match = re.search(TWELVE_WORD_PATTERN, text, re.IGNORECASE)
    return match.group(0) if match else None

# ===== TELEGRAM COMMANDS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued"""
    welcome_text = """
🎯 **Word Race Bot** 🎯

Send me a voice or video message and I'll extract any 12-word phrase from it!

**Game Commands:**
/race_start - Start a new race with your friend
/race_status - Check current race status
/race_reset - Reset the race

First person to send a message containing 12 words wins!
    """
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def race_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a new race"""
    global race_active, winner, first_transcript
    race_active = True
    winner = None
    first_transcript = None
    await update.message.reply_text("🏁 **RACE STARTED!** 🏁\n\nFirst to send a voice/video message with 12 words wins!", parse_mode="Markdown")

async def race_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check current race status"""
    global race_active, winner
    if winner:
        await update.message.reply_text(f"🏆 Race is over! Winner: **{winner}** 🏆", parse_mode="Markdown")
    elif race_active:
        await update.message.reply_text("🏎️ Race is ACTIVE! No winner yet. Send your voice message!")
    else:
        await update.message.reply_text("⏸️ No active race. Start one with /race_start")

async def race_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset the race"""
    global race_active, winner, first_transcript
    race_active = False
    winner = None
    first_transcript = None
    await update.message.reply_text("🔄 Race has been reset. Start a new one with /race_start")

async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice and video messages"""
    global race_active, winner, first_transcript
    
    user = update.effective_user
    username = user.first_name or user.username
    
    # Check if race is active
    if not race_active:
        await update.message.reply_text("⏸️ No active race. Start one with /race_start first!")
        return
    
    # Check if someone already won
    if winner:
        await update.message.reply_text(f"🏆 Race already over! **{winner}** already won!", parse_mode="Markdown")
        return
    
    # Send processing message
    processing_msg = await update.message.reply_text("🎤 Processing your message... Extracting words...")
    
    temp_file = None
    
    try:
        # Get the file
        if update.message.voice:
            file = await update.message.voice.get_file()
            file_ext = ".ogg"
        elif update.message.video:
            file = await update.message.video.get_file()
            file_ext = ".mp4"
        else:
            await processing_msg.edit_text("❌ Please send a voice or video message")
            return
        
        # Download to temporary file
        await processing_msg.edit_text("📥 Downloading audio...")
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            temp_path = tmp_file.name
        
        # Download the file
        await file.download_to_drive(temp_path)
        
        # Check if file was downloaded
        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            await processing_msg.edit_text("❌ Failed to download audio file")
            return
        
        await processing_msg.edit_text("🔊 Transcribing audio...")
        
        # Transcribe
        transcript = await transcribe_audio(temp_path)
        
        # Clean up temp file
        try:
            os.unlink(temp_path)
        except:
            pass
        
        # Look for 12 words
        twelve_words = find_twelve_words(transcript)
        
        if twelve_words:
            # THIS PERSON WINS!
            winner = username
            first_transcript = transcript
            
            await processing_msg.edit_text(
                f"🏆 **WINNER!** 🏆\n\n"
                f"🎉 {username} found the 12 words FIRST!\n\n"
                f"📝 **The winning phrase:**\n`{twelve_words}`\n\n"
                f"📄 **Full transcript:**\n{transcript[:500]}"
            )
        else:
            # No 12 words found, show what they said
            await processing_msg.edit_text(
                f"❌ No 12-word phrase found in {username}'s message.\n\n"
                f"📝 **Transcript:**\n{transcript[:300]}\n\n"
                f"Keep trying!"
            )
            
    except Exception as e:
        print(f"Error details: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up temp file if it exists
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass
                
        await processing_msg.edit_text(f"❌ Error: {str(e)[:100]}")

# ===== MAIN FUNCTION =====

def main():
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("race_start", race_start))
    application.add_handler(CommandHandler("race_status", race_status))
    application.add_handler(CommandHandler("race_reset", race_reset))
    
    # Add handler for voice and video messages
    application.add_handler(MessageHandler(filters.VOICE | filters.VIDEO, handle_media))
    
    # Start the bot
    print("🤖 Bot is starting...")
    application.run_polling()

if __name__ == "__main__":
    main()