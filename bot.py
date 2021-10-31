# Utilities
import os
import logging
import attr
import hashlib
from datetime import date
from enum import Enum

# Telegram bot API
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

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
	INPUT_START_DATE 	= 5	
	INPUT_END_DATE 		= 6
	INPUT_STATE_END 	= 7

# State enum for authentication steps
class AuthState(Enum):
	AUTH_STATE_IDLE 		= 0
	AUTH_IS_AUTHENTICATING 	= 1
	AUTH_IS_AUTHENTICATED 	= 2

# Data class for consulta objects
@attr.s
class Consulta:

	# Date values
	start_date:date 	= attr.ib(default = None)
	end_date:date 		= attr.ib(default = None)

	# Names and course information
	assistant_name:str 	= attr.ib(converter=str, default="")
	auxiliary_name:str 	= attr.ib(converter=str, default="")
	student_name: str 	= attr.ib(converter=str, default="")
	course_name:str 	= attr.ib(converter=str, default="N/A")

class GeconsultasBot:

	def __init__(self):

		# Set initial values
		self.consulta 		= Consulta()
		self.input_state 	= InputState.INPUT_STATE_IDLE
		self.auth_state 	= AuthState.AUTH_STATE_IDLE

		# Fetch API token and hashed password from environment variables
		self.token 		= os.getenv("T_API_TOKEN")
		self.auth_hash 	= os.getenv("T_AUTH_HASH")

		# Halt runtime if token or hash aren't set
		if not self.token or not self.auth_hash:
			raise RuntimeError

		# Instantiate Updater and Dispatcher
		self.updater 	= Updater(self.token, use_context=True)
		self.dispatcher = self.updater.dispatcher

	def run(self):

		self.add_handlers()

		# Build state-function map for input steps
		self.input_state_map = {
			InputState.INPUT_STATE_IDLE: 	self.handle_input_idle,
			InputState.INPUT_STUDENT_NAME: 	self.handle_student_name,
			InputState.INPUT_COURSE_NAME: 	self.handle_course_name,
			InputState.INPUT_ASSIST_NAME: 	self.handle_assist_name,
			InputState.INPUT_AUX_NAME:		self.handle_aux_name,
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

		self.updater.start_polling()
		self.updater.idle()

	def add_handlers(self):

		# Create and add command handlers
		start_command 		= CommandHandler("start", self.start)
		help_command 		= CommandHandler("help", self.show_help)
		register_command 	= CommandHandler("registrar", self.register)
		restart_command 	= CommandHandler("restart", self.restart)
		auth_command		= CommandHandler("auth", self.auth)
		logout_command		= CommandHandler("auth", self.logout)

		# Create message handler
		message_handler = MessageHandler(Filters.text, self.handle_message)

		# data and flow
		self.dispatcher.add_handler(start_command)
		self.dispatcher.add_handler(help_command)
		self.dispatcher.add_handler(register_command)
		self.dispatcher.add_handler(restart_command)

		# authentication
		self.dispatcher.add_handler(auth_command)
		self.dispatcher.add_handler(logout_command)

		# message handler
		self.dispatcher.add_handler(message_handler)

	# Command handlers

	def start(self, update, context):

		# Start from the top; reset everything and show help
		self.restart(update, context, True)
		self.logout(update, context, True)
		self.show_help(update, context)

	def show_help(self, update, context):

		help_text = "¡Hola! Soy el ayudante virtual de Geconsultas 🙂\n" + \
					"Conmigo puedes ingresar los datos de tu Geconsulta de forma automatizada, sin rollos 😎\n" + \
					"➡️ Usa el comando /auth para autenticar tu chat 🔐\n" + \
					"➡️ Usa el comando /registrar para ingresar datos 📝\n" + \
					"➡️ Usa el comando /restart para borrar los datos y comenzar desde cero 🔄"
		update.message.reply_text(help_text)

	def handle_message(self, update, context):

		state_function = None

		# Take inputs only when permitted
		if self.input_state.value > InputState.INPUT_STATE_IDLE.value and self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:
			state_function = self.input_state_map[self.input_state]

		elif self.auth_state == AuthState.AUTH_IS_AUTHENTICATING:
			state_function = self.auth_state_map[self.auth_state]

		# If a state function has been specified, call it and pass down parameters
		if state_function is not None:
			state_function(update, context)

	def register(self, update, context):

		# Halt if user is not authenticated
		if self.auth_state != AuthState.AUTH_IS_AUTHENTICATED:
			update.message.reply_text("Por favor, usa el comando /auth para autenticar tu chat primero ✅")
			return

		# If handling a previous entry flow, clobber old data
		if self.input_state.value > InputState.INPUT_STATE_IDLE.value:
			self.consulta = Consulta()
		
		# Log data entry attempt
		logger.info("Data entry requested by user {id}".format(id=update.message.chat.id))

		# Set input state and update user
		self.input_state = InputState.INPUT_STUDENT_NAME
		state_function = self.input_state_map[self.input_state]

		update.message.reply_text("Por favor, sigue los pasos para registrar tu consulta 🙂")
		update.message.reply_text("Introduce el nombre del estudiante 📖⬇️")

	def restart(self, update, context, noupdate=False):

		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:

			# Reset input state and input object
			self.consulta = Consulta()
			self.input_state = InputState.INPUT_STATE_IDLE

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
		logger.info("Auth requested by user {id}".format(id=update.message.chat.id))

		# Set Auth state and update user
		self.auth_state = AuthState.AUTH_IS_AUTHENTICATING
		update.message.reply_text("Por favor, introduce la contraseña 🙂")

	def logout(self, update, context, noupdate=False):
		if self.auth_state == AuthState.AUTH_IS_AUTHENTICATED:

			# Reset state and update user
			self.auth_state = AuthState.AUTH_STATE_IDLE

			if not noupdate:
				update.message.reply_text("Sesión cerrada con éxito 🙂 ¡Nos vemos!")

	# Auth handlers

	def handle_auth_idle(self, update, context):
		pass

	def handle_authenticating(self, update, context):
		if update.message.text is not None:

			# Compute the password hash and evaluate against the pre-set value
			password_hash = self.hash_string(update.message.text)
			if password_hash == self.auth_hash:
				self.auth_state = AuthState.AUTH_IS_AUTHENTICATED

				# Log succesful authentication
				logger.info("Auth completed by user {id}".format(id=update.message.chat.id))
				update.message.reply_text("¡Autenticación completa! 😎 Ahora puedes usar /registrar para comenzar la entrada de datos.")
			else:

				# Log failed authentication attempt
				logger.info("Auth attempt failed by user {id}".format(id=update.message.chat.id))
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

			self.input_state = InputState.INPUT_COURSE_NAME
			update.message.reply_text("¡Genial! Ahora dime el código de materia ☺️")

		else:
			reply_text = "Parece que no enviaste un nombre válido 🤔\n" + \
						 "Por favor, inténtalo de nuevo 👇"
			update.message.reply_text(reply_text)

	def handle_course_name(self, update, context):
		# TODO: implement this stuff :P
		print("sam::course_name")

	def handle_assist_name(self, update, context):
		pass

	def handle_aux_name(self, update, context):
		pass

	def handle_start_date(self, update, context):
		pass

	def handle_end_date(self, update, context):
		pass

	def handle_input_end(self, update, context):
		pass

	# Auxiliary methods
	def hash_string(self, string):

		# Return a SHA-256 hash of the given string
		return hashlib.sha256(string.encode('utf-8')).hexdigest()

if __name__ == "__main__":
	bot = GeconsultasBot()
	bot.run()