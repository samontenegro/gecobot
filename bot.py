# Utilities
import os
import logging
import attr
import hashlib
from datetime import date
from enum import Enum

# Telegram bot API
import telegram
from telegram import ReplyKeyboardMarkup
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

# Support modules
from sheetmanager import SheetManager, DataSheetEnum
from inlineselector import InlineSelector
from inlinedateselector import InlineDateSelector

# Instantiate and configure logger
logging.basicConfig(
	level = logging.INFO, format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s,"
)

logger = logging.getLogger()

# State enum for data entry steps
class InputState(Enum):
	INPUT_STATE_IDLE 	= 0
	INPUT_STUDENT_NAME 	= 1
	INPUT_COURSE_NAME 	= 2
	INPUT_ASSIST_NAME 	= 3
	INPUT_AUX_NAME 		= 4
	INPUT_RECEIVED_DATE = 5
	INPUT_START_DATE 	= 6	
	INPUT_END_DATE 		= 7
	INPUT_STATE_END 	= 8

# State enum for authentication steps
class AuthState(Enum):
	AUTH_STATE_IDLE 		= 0
	AUTH_IS_AUTHENTICATING 	= 1
	AUTH_IS_AUTHENTICATED 	= 2

# Utility method for computing SHA-256 hash
def hash_string(string):

	# Return a SHA-256 hash of the given string
	return hashlib.sha256(string.encode('utf-8')).hexdigest()

# Data class for consulta objects
@attr.s
class Consulta:

	# Date values
	received_date:str 	= attr.ib(converter=str, default="")
	start_date:str 		= attr.ib(converter=str, default="")
	end_date:str 		= attr.ib(converter=str, default="")

	# Names and course information
	assistant_name:str 	= attr.ib(converter=str, default="")
	auxiliary_name:str 	= attr.ib(converter=str, default="")
	student_name:str 	= attr.ib(converter=str, default="")
	course_name:str 	= attr.ib(converter=str, default="N/A")

class GeconsultaInstanceBot:

	def __init__(self, user_id, auth_hash, sheet_manager):

		# Set initial values
		self.user_id 		= user_id
		self.consulta 		= Consulta()
		self.input_state 	= InputState.INPUT_STATE_IDLE
		self.auth_state 	= AuthState.AUTH_STATE_IDLE

		# Sheet manager reference for pushing requests
		self.sheet_manager = sheet_manager

		# Receive password hash for authentication
		self.auth_hash 	= auth_hash

		# Instantiate inline selectors
		course_name_field = DataSheetEnum.COURSE_NAME
		assist_name_field = DataSheetEnum.ASSIST_NAME
		self.course_name_selector = InlineSelector(sheet_manager.get_data_from_field_functor(course_name_field))
		self.assist_name_selector = InlineSelector(sheet_manager.get_data_from_field_functor(assist_name_field))

		# Instantiate date selector
		self.date_selector = InlineDateSelector()

		# Instantiate selector map
		self.selector_map = {}

		# Halt runtime if hash isn't present
		if not self.auth_hash:
			raise RuntimeError

		self.run()

	def run(self):

		# Build state-function map for input steps
		self.input_state_map = {
			InputState.INPUT_STATE_IDLE: 	self.handle_input_idle,
			InputState.INPUT_STUDENT_NAME: 	self.handle_student_name,
			InputState.INPUT_COURSE_NAME: 	self.handle_course_name,
			InputState.INPUT_ASSIST_NAME: 	self.handle_assist_name,
			InputState.INPUT_AUX_NAME:		self.handle_aux_name,
			InputState.INPUT_RECEIVED_DATE:	self.handle_received_date,
			InputState.INPUT_START_DATE:	self.handle_start_date,
			InputState.INPUT_END_DATE:		self.handle_end_date,
			InputState.INPUT_STATE_END: 	self.handle_input_end
		}

		# Build state-function map for auth steps
		self.auth_state_map = {
			AuthState.AUTH_STATE_IDLE: 			self.handle_auth_idle,
			AuthState.AUTH_IS_AUTHENTICATING: 	self.handle_authenticating,
			AuthState.AUTH_IS_AUTHENTICATED: 	self.handle_is_authenticated
		}

	# Command handlers
	def start(self, update, context):

		# Start from the top; reset everything and show help
		self.restart(update, context, True)
		self.logout(update, context, True)
		self.show_help(update, context)

		logger.info("Bot instance started by user {id}".format(id=update.message.from_user.id))

	def show_help(self, update, context):

		help_text = "¡Hola! Soy el ayudante virtual de Geconsultas 🙂\n" + \
					"Conmigo puedes ingresar los datos de tu Geconsulta de forma automatizada, sin rollos 😎\n" + \
					"➡️ Usa el comando /auth para autenticar tu chat 🔐\n" + \
					"➡️ Usa el comando /registrar para ingresar datos 📝\n" + \
					"➡️ Usa el comando /restart para borrar los datos y comenzar desde cero 🔄"
		update.message.reply_text(help_text)

	def register(self, update, context):

		# Halt if user is not authenticated
		if self.auth_state != AuthState.AUTH_IS_AUTHENTICATED:
			update.message.reply_text("Por favor, usa el comando /auth para autenticar tu chat primero ✅")
			return

		# If handling a previous entry flow, clobber old data
		if self.input_state.value > InputState.INPUT_STATE_IDLE.value:
			self.consulta = Consulta()
		
		# Log data entry attempt
		logger.info("Data entry requested by user {id}".format(id=update.message.from_user.id))

		# Set input state and update user
		self.input_state = InputState.INPUT_STUDENT_NAME
		state_function = self.input_state_map[self.input_state]

		update.message.reply_text("Por favor, sigue los pasos para registrar tu consulta 🙂")
		update.message.reply_text("Introduce el nombre del estudiante 📖")

	def restart_inline_selectors(self):
		self.course_name_selector.reset()
		self.assist_name_selector.reset()
		self.date_selector.reset()
		self.selector_map = {}

	def restart(self, update, context, noupdate=False):

		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:

			# Log data entry abort
			if self.input_state.value < InputState.INPUT_STATE_END.value:
				logger.info("Data entry aborted by user {id}".format(id=update.message.from_user.id))

			# Reset input state and input object
			self.consulta = Consulta()
			self.input_state = InputState.INPUT_STATE_IDLE

			# Reset inline objects to their original state
			self.restart_inline_selectors()

			# User update
			if not noupdate:
				update.message.reply_text("¡Datos reseteados!")

	def auth(self, update, context):

		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:
			reply_text = "Parece que ya estás autenticado 🙂\n" + \
						 "Para registrar tu consulta, usa el comando /register 📝"
			update.message.reply_text(reply_text)
			return

		# Log authentication attempt
		logger.info("Auth requested by user {id}".format(id=update.message.from_user.id))

		# Set Auth state and update user
		self.auth_state = AuthState.AUTH_IS_AUTHENTICATING
		update.message.reply_text("Por favor, introduce la contraseña 🙂")

	def logout(self, update, context, noupdate=False):
		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:

			# Reset state and update user
			self.restart(update, context, True)
			self.auth_state = AuthState.AUTH_STATE_IDLE

			logger.info("User {id} has logged out succesfully".format(id=update.message.from_user.id))

			if not noupdate:
				update.message.reply_text("Sesión cerrada con éxito 🙂 ¡Nos vemos!")

			# If logout is succesful, return True
			return True

		# If logout is not performed, return False
		return False

	# Inline handler
	def handle_inline_query(self, update, context):
		if update.callback_query.message.message_id not in self.selector_map:
			self.selector_map[update.callback_query.message.message_id] = self.current_selector()

		# Only accept callback queries as input
		if update.callback_query.data is not None:
			state_function = self.input_state_map[self.input_state]
			selector = self.selector_map[update.callback_query.message.message_id]
			state_function(update, context, selector)

	# Message handler
	def handle_message(self, update, context):
		state_function = None

		# Take inputs only when permitted
		if self.input_state.value > InputState.INPUT_STATE_IDLE.value and self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:
			state_function = self.input_state_map[self.input_state]

		elif self.auth_state == AuthState.AUTH_IS_AUTHENTICATING:
			state_function = self.auth_state_map[self.auth_state]

		if self.auth_state.value > AuthState.AUTH_IS_AUTHENTICATING.value:
			logger.info("Handling message {msg} by user {id}".format(msg = update.message.text, id=update.message.from_user.id))

		# If a state function has been specified, call it and pass down parameters
		if state_function is not None:
			state_function(update, context)

	# Auth handlers
	def handle_auth_idle(self, update, context):
		pass

	def handle_authenticating(self, update, context):
		if update.message.text is not None:

			# Compute the password hash and evaluate against the pre-set value
			password_hash = hash_string(update.message.text)
			if password_hash == self.auth_hash:
				self.auth_state = AuthState.AUTH_IS_AUTHENTICATED

				# Log succesful authentication
				logger.info("Auth completed by user {id}".format(id=update.message.from_user.id))
				update.message.reply_text("¡Autenticación completa! 😎 Ahora puedes usar /registrar para comenzar la entrada de datos 📝")
			else:

				# Log failed authentication attempt
				logger.info("Auth attempt failed by user {id}".format(id=update.message.from_user.id))
				update.message.reply_text("Contraseña inválida, por favor intenta nuevamente.")


	def handle_is_authenticated(self, update, context):
		pass

	# Input handlers
	def handle_input_idle(self, update, context):
		pass

	def handle_student_name(self, update, context):
		
		if update.message.text is not None:

			student_name = update.message.text
			self.consulta.student_name = student_name

			# Update state
			self.input_state = InputState.INPUT_COURSE_NAME

			# Create inline keyboard and reply
			self.course_name_selector.fetch_data()
			keyboard = self.course_name_selector.get_inline_keyboard()
			update.message.reply_text("¡Genial! Selecciona el nombre de la materia ✒️", reply_markup = keyboard)

		else:
			reply_text = "Parece que no enviaste un nombre válido 🤔\n" + \
						 "Por favor, inténtalo de nuevo 👇"
			update.message.reply_text(reply_text)

	def handle_course_name(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.course_name = data
				self.input_state = InputState.INPUT_ASSIST_NAME
				
				self.assist_name_selector.fetch_data()
				keyboard = self.assist_name_selector.get_inline_keyboard()
				update.callback_query.message.reply_text("¡Muy bien! Selecciona el nombre del miembro encargado 🤓", reply_markup = keyboard)


	def handle_assist_name(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.assistant_name = data
				self.input_state = InputState.INPUT_AUX_NAME
				
				# Reutilize the same selector
				self.assist_name_selector.reset()
				self.assist_name_selector.fetch_data()
				keyboard = self.assist_name_selector.get_inline_keyboard()
				update.callback_query.message.reply_text("¡Excelente! Selecciona el nombre del miembro auxiliar 🤝", reply_markup = keyboard)

	def handle_aux_name(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.auxiliary_name = data
				self.input_state = InputState.INPUT_RECEIVED_DATE
				
				# Use the date selector
				keyboard = self.date_selector.get_inline_keyboard()
				update.callback_query.message.reply_text("¡Recibido! Ahora selecciona la fecha en que se recibió la consulta 📆", reply_markup = keyboard)

	def handle_received_date(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.received_date = data
				self.input_state = InputState.INPUT_START_DATE
				
				# Reutilize the date selector
				self.date_selector.reset()
				keyboard = self.date_selector.get_inline_keyboard()
				update.callback_query.message.reply_text("¡Buenísimo! Selecciona la fecha en que se atendió la consulta 📆", reply_markup = keyboard)

	def handle_start_date(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.start_date = data
				self.input_state = InputState.INPUT_END_DATE
				
				# Reutilize the date selector
				self.date_selector.reset()
				keyboard = self.date_selector.get_inline_keyboard()
				update.callback_query.message.reply_text("¡Perfecto! Por último, selecciona la fecha en que terminó la consulta 📆", reply_markup = keyboard)

	def handle_end_date(self, update, context, selector = None):

		# Only accept callback queries as input
		if update.callback_query is not None and selector is not None:
			data = selector.handle_callback_query(update, context)

			# If data is extracted, push it and change state
			if data is not None:
				self.consulta.end_date = data
				self.input_state = InputState.INPUT_STATE_END

				logger.info("Data entry completed by user {id}".format(id=update.callback_query.from_user.id))

				# self.consulta should be ready at this point! Send a Sheet Manager request!
				self.sheet_manager.request_input(self.consulta)
				update.callback_query.message.reply_text("¡Tu consulta ha sido enviada! 🎉🎉")
				update.callback_query.message.reply_text("Puedes confirmar luego en la spreadsheet si tu consulta ha sido procesada correctamente 🔎")
				update.callback_query.message.reply_text("¡Que tengas un buen día! ✨ Recuerda que puedes usar /registrar para subir una nueva consulta 🙂")

				# Restart bot instance
				self.restart(update, context, True)

	def handle_input_end(self, update, context):
		pass	

	# Auxiliary Methods
	def current_selector(self):

		# No selectors are exposed if not authenticated
		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:
			
			# Determine the corresponding selector
			if self.input_state == InputState.INPUT_COURSE_NAME:
				return self.course_name_selector

			elif self.input_state == InputState.INPUT_ASSIST_NAME:
				return self.assist_name_selector

			elif self.input_state == InputState.INPUT_AUX_NAME:
				return self.assist_name_selector

			elif self.input_state == InputState.INPUT_RECEIVED_DATE:
				return self.date_selector

			elif self.input_state == InputState.INPUT_START_DATE:
				return self.date_selector

			elif self.input_state == InputState.INPUT_END_DATE:
				return self.date_selector

		return None

class GeconsultasBot():

	def __init__(self):

		# Fetch API token and hashed password from environment variables
		self.token 		= os.getenv("T_API_TOKEN")
		self.auth_hash 	= os.getenv("T_AUTH_HASH")

		# Halt runtime if token or hash aren't set
		if not self.token or not self.auth_hash:
			raise RuntimeError

		# Create active user map
		self.user_map = {}

		# Create sheets object and retrieve data
		self.sheet_manager = SheetManager()

		# Instantiate Updater and Dispatcher
		self.updater 	= Updater(self.token, use_context=True)
		self.dispatcher = self.updater.dispatcher

	def run(self):

		# Add handlers and start bot
		self.add_handlers()

		self.updater.start_polling()
		self.updater.idle()

	def add_handlers(self):

		# Create and add command handlers
		start_command 		= CommandHandler("start", 		self.start)
		help_command 		= CommandHandler("help", 		self.show_help)
		register_command 	= CommandHandler("registrar", 	self.register)
		restart_command 	= CommandHandler("restart", 	self.restart)
		auth_command		= CommandHandler("auth", 		self.auth)
		logout_command		= CommandHandler("logout", 		self.logout)

		# Create message handler
		message_handler = MessageHandler(Filters.text, self.handle_message)

		# Data and flow
		self.dispatcher.add_handler(start_command)
		self.dispatcher.add_handler(help_command)
		self.dispatcher.add_handler(register_command)
		self.dispatcher.add_handler(restart_command)

		# Authentication
		self.dispatcher.add_handler(auth_command)
		self.dispatcher.add_handler(logout_command)

		# Message handler
		self.dispatcher.add_handler(message_handler)

		# Inline handler
		self.dispatcher.add_handler(CallbackQueryHandler(self.handle_inline_query))

	# Inline query handler
	def handle_inline_query(self, update, context):
		self.call_instance_method(update, context, "handle_inline_query", True)

	# Command Handlers
	def start(self, update, context):
		if update.message.from_user.id is not None:

			# Capture chat ID and assign a new instance bot if it's not already present
			user_id = update.message.from_user.id
			if user_id not in self.user_map:
				self.user_map[user_id] = GeconsultaInstanceBot(user_id, self.auth_hash, self.sheet_manager)

			self.call_instance_method(update, context, "start")

	def show_help(self, update, context):
		self.call_instance_method(update, context, "show_help")

	def register(self, update, context):
		self.call_instance_method(update, context, "register")

	def restart(self, update, context):
		self.call_instance_method(update, context, "restart")

	def auth(self, update, context):
		self.call_instance_method(update, context, "auth")

	def logout(self, update, context):
		logged_out = self.call_instance_method(update, context, "logout")
		if update.message.from_user.id in self.user_map and logged_out:
			self.user_map.pop(update.message.from_user.id)

	# Message handlers
	def handle_message(self, update, context):
		self.call_instance_method(update, context, "handle_message")

	# Auxiliary methods
	def call_instance_method(self, update, context, method, is_inline = False):

		# No bot instance by default
		user_bot_instance = None

		# Try to resolve user_id from CallbackQuery object first
		if is_inline and update.callback_query.from_user.id in self.user_map:
			user_bot_instance = self.user_map[update.callback_query.from_user.id]

		# Else, try to resolve user_id from Message object
		elif update.message.from_user.id in self.user_map:
			user_bot_instance = self.user_map[update.message.from_user.id]

		# If bot instance is found and has method, call it
		if user_bot_instance is not None and hasattr(user_bot_instance, method):
				return getattr(user_bot_instance, method)(update, context)

if __name__ == "__main__":
	bot = GeconsultasBot()
	bot.run()