import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Name of the main spreadsheet
MAIN_SPREADSHEET_NAME = "Registro De Geconsultas V2"

# Expected worksheet IDs
WORKSHEET_DATA = "DATA"
WORKSHEET_REGISTER = "REGISTRO"


# Simple class for managing spreadsheet operations using Google Sheets API
class SheetManager():

	def __init__(self):

		# Define API scope for our script
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
			self.creds = ServiceAccountCredentials.from_json_keyfile_name("cred.gkey", self.scope)
		except FileNotFoundError:
			print("Credentials file was not found! Please check your working directory for cred.gkey")

		if self.creds is None:
			raise RuntimeError

		self.client = gspread.authorize(self.creds)

		# Get default sheet reference
		self.spreadsheet = self.client.open(MAIN_SPREADSHEET_NAME)

		# Get worksheet references
		self.worksheet_data 	= self.spreadsheet.worksheet(WORKSHEET_DATA)
		self.worksheet_register = self.spreadsheet.worksheet(WORKSHEET_REGISTER)

		# @salonso testing
		print(self.worksheet_data.get_all_records())
		print(self.worksheet_register.get_all_records())

if __name__ == "__main__":
	manager = SheetManager()

