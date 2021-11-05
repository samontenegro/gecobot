from enum import Enum
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Default consts
SELECTOR_ROWS_DEFAULT 		= 5
SELECTOR_RIGHT_BUTTON_TAG 	= "»"
SELECTOR_LEFT_BUTTON_TAG 	= "«"

class InlineSelectorAction(Enum):
	ACTION_RIGHT = "$right"
	ACTION_LEFT = "$left"

class InlineSelectorState(Enum):
	IDLE 				= 0
	SELECTION_ACTIVE 	= 1
	SELECTION_COMPLETE 	= 2


class InlineSelector():
	def __init__(self, data_function, n_rows = SELECTOR_ROWS_DEFAULT):

		# Set inital state
		self.selector_state = InlineSelectorState.IDLE
		self.data_function 	= data_function
		self.page_length 	= n_rows
		self.page_index		= 0

	def is_action(string):
		return string.startswith("$")

	def get_inline_keyboard(self):

		# Get latest data
		self.fetch_data()

		# Create fixed buttons
		right_button 	= InlineKeyboardButton(SELECTOR_RIGHT_BUTTON_TAG, callback_data = InlineSelectorAction.ACTION_RIGHT.value)
		left_button 	= InlineKeyboardButton(SELECTOR_LEFT_BUTTON_TAG, callback_data = InlineSelectorAction.ACTION_LEFT.value)

		# Create data buttons from page index
		buttons = [[InlineKeyboardButton(x, callback_data = x)] for x in self.data[self.page_index * self.page_length : self.page_length]]

		# Append dynamic buttons and build keyboard
		buttons.append([left_button, right_button])
		keyboard = InlineKeyboardMarkup(buttons)

		# Set state
		self.selector_state = InlineSelectorState.SELECTION_ACTIVE

		return keyboard

	def fetch_data(self):

		# Fetch latest data, and filter out empty strings
		self.data = list(filter(lambda val : val != "", self.data_function()))

	def handle_page_change(self, is_right = True):
		pass

	def handle_callback_query(self, update, context):
		pass


