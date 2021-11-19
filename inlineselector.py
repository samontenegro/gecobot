from enum import Enum
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

# Default consts
SELECTOR_ROWS_DEFAULT = 4

class InlineSelectorAction(Enum):
	ACTION_RIGHT 	= ("»", "$right")
	ACTION_LEFT 	= ("«", "$left")
	ACTION_NO_OP 	= ("", "$noop")

	@classmethod
	def has_action(cls, action_string):
		return action_string in [member.value[1] for member in cls]

	def tag(member):
		return member.value[0]

	def action_string(member):
		return member.value[1]

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
		self.data 			= None

	def is_action(self, string):
		return string.startswith("$")

	def is_action_valid(self, action):

		# Check for no-ops
		if action == InlineSelectorAction.ACTION_NO_OP.action_string():
			return False

		# Check for bounds first
		if action == InlineSelectorAction.ACTION_LEFT.action_string() and self.page_index == 0:
			return False

		if action == InlineSelectorAction.ACTION_RIGHT.action_string() and (self.page_index + 1) * self.page_length >= len(self.data):
			return False

		return True

	def get_inline_keyboard(self):

		# Return None if data is not present
		if self.data is None:
			return None

		# Create fixed buttons
		right_button 	= InlineKeyboardButton(InlineSelectorAction.ACTION_RIGHT.tag(), callback_data = InlineSelectorAction.ACTION_RIGHT.action_string())
		left_button 	= InlineKeyboardButton(InlineSelectorAction.ACTION_LEFT.tag(), callback_data = InlineSelectorAction.ACTION_LEFT.action_string())

		# Create data buttons from page index
		buttons = [[InlineKeyboardButton(x, callback_data = x)] for x in self.data[self.page_index * self.page_length : (self.page_index + 1) * self.page_length]]

		# Append dynamic buttons and build keyboard
		buttons.append([left_button, right_button])
		keyboard = InlineKeyboardMarkup(buttons)

		# Set state
		self.selector_state = InlineSelectorState.SELECTION_ACTIVE

		return keyboard

	def fetch_data(self):

		# Fetch latest data, and filter out empty strings
		self.data = list(filter(lambda val : val != "", self.data_function()))

	def handle_selector_action(self, update, context, action):
		
		is_valid = self.is_action_valid(action)

		# If invalid, do nothing
		if not is_valid:
			return

		# Update page index
		step = 1 if action == InlineSelectorAction.ACTION_RIGHT.action_string() else -1
		self.page_index += step

		# Update reply markup with new keyboard
		keyboard = self.get_inline_keyboard()
		update.callback_query.edit_message_reply_markup(reply_markup = keyboard)
		update.callback_query.answer()

	def handle_callback_query(self, update, context):
		
		# Safety check
		if update.callback_query.data is not None and self.selector_state == InlineSelectorState.SELECTION_ACTIVE:

			# Get data
			data_string = update.callback_query.data

			# Check if is action
			if self.is_action(data_string) and InlineSelectorAction.has_action(data_string):
				self.handle_selector_action(update, context, data_string)
				return None

			# If it's not an action, collapse keyboard to choide made
			default_button = InlineKeyboardButton(data_string, callback_data = InlineSelectorAction.ACTION_NO_OP.action_string())
			keyboard = InlineKeyboardMarkup([[default_button]])
			update.callback_query.edit_message_reply_markup(reply_markup = keyboard)
			update.callback_query.answer()

			# Return data
			self.selector_state = InlineSelectorState.SELECTION_COMPLETE
			return data_string

	def reset(self):

		# reset state of selector
		self.selector_state = InlineSelectorState.IDLE
		self.page_index		= 0
		self.data 			= None
				

