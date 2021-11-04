import gspread
from heartbeat import Heartbeat
from enum import Enum
from oauth2client.service_account import ServiceAccountCredentials

# Manager update interval (in seconds)
UPDATE_INTERVAL = 5

# Name of the main spreadsheet
MAIN_SPREADSHEET_NAME = "Registro De Geconsultas V2"

# Expected worksheet IDs
WORKSHEET_DATA 		= "DATA"
WORKSHEET_REGISTER 	= "REGISTRO"

# Utility values
REGISTRY_INPUT_ROW_OFFSET = 4

# Base Enum class for sheet enumerations
class SheetEnum(Enum):

	# Generic getters for returning enum values
	def get_index(member):
		return member.value[0]

	def get_key(member):
		return member.value[1]

# Column enumerations for the DATA sheet (index, column_key)
class DataSheetEnum(SheetEnum):
	ASSIST_NAME = (0, "MIEMBROS")
	COURSE_NAME = (1, "MATERIAS")
	COURSE_CODE = (2, "CODIGO")

# Column enumerations for the REGISTER sheet (index, column_key)
class RegisterSheetEnum(SheetEnum):
	STUDENT_NAME 	= (0, "Nombre")
	COURSE_NAME 	= (1, "Materia")
	COURSE_CODE 	= (2, "Código")
	RECEIVED_DATE 	= (3, "Hora Recibida")
	START_DATE 		= (4, "Hora Atendida")
	END_DATE 		= (5, "Hora Completada")
	RESPONSE_TIME 	= (6, "Tiempo de Respuesta")
	DURATION_TIME 	= (7, "Duración de Consulta")
	ASSIST_NAME 	= (8, "Miembro Encargado")
	AUX_NAME 		= (9, "Miembro de Soporte")

# Enum for sheet instance state
class SheetState(Enum):
	SHEET_NOT_INITIALIZED 	= -1
	SHEET_READY 			= 0


class Sheet():

	def __init__(self, client):

		self.sheet_state = SheetState.SHEET_NOT_INITIALIZED

		# halt execution if client is not given
		if client is None:
			raise RuntimeError 

		try:
			# Get default sheet reference
			self.spreadsheet = client.open(MAIN_SPREADSHEET_NAME)

			# Get worksheet references
			self.worksheet_data 	= self.spreadsheet.worksheet(WORKSHEET_DATA)
			self.worksheet_register = self.spreadsheet.worksheet(WORKSHEET_REGISTER)

			# Sheet object is ready
			self.sheet_state = SheetState.SHEET_READY

		except Exception as e:
			print("Sheet::__init__ Sheet instance init failed; check spreadsheet / worksheet names")

	# Helper method to check if instance is ready
	def is_ready(self):
		return self.sheet_state == SheetState.SHEET_READY

	# Method for entering consultas into the REGISTER worksheet
	def enter_row_data(self, consulta = None):
		if not self.is_ready():
			return

		# @salonso testing
		self.worksheet_register.insert_row([consulta, 2, "=A2+B2"], REGISTRY_INPUT_ROW_OFFSET, "USER_ENTERED")

# Simple class for managing spreadsheet operations using Google Sheets API
class SheetManager():

	def __init__(self):

		# Define API scope for our manager
		self.scope = [
			"https://spreadsheets.google.com/feeds",
			"https://www.googleapis.com/auth/spreadsheets",
			"https://www.googleapis.com/auth/drive.file",
			"https://www.googleapis.com/auth/drive"
		]

		# Default values for credentials and G Sheet client
		self.creds 	= None
		self.client = None

		try:
			# Retrieve credentials file and authenticate client
			self.creds 	= ServiceAccountCredentials.from_json_keyfile_name("cred.gkey", self.scope)
			self.client = gspread.authorize(self.creds)
			self.sheet 	= Sheet(self.client) 

		except FileNotFoundError:
			print("SheetManager::__init__ Credentials file was not found! Please check your working directory for cred.gkey")

		if self.creds is None or self.client is None:
			raise RuntimeError

		# Input variables
		self.input_stack = []

		# Create timer instance and register self.update
		self.heartbeat = Heartbeat(UPDATE_INTERVAL)
		self.heartbeat.register_listener("manager_update", self.update)

		# Start timer
		self.heartbeat.start_timer()

	# Push 'consulta' objects onto the stack
	def request_input(self, consulta):
		if consulta is not None:
			self.input_stack.append(consulta)

	def update(self):

		# If input stack contains more than one element, process elements at once
		if len(self.input_stack):
			self.process_items()

	def process_items(self):

		# Process all items written to the stack sequentially
		while len(self.input_stack) > 0:

			# Get first element
			consulta_item = self.input_stack.pop(0)

			# Request an insert_row call with the consulta data
			self.sheet.enter_row_data(consulta_item)

if __name__ == "__main__":

	# Instantiate Sheet Manager
	manager = SheetManager()

	
	


